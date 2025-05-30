package com.example.ernetlink;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import android.Manifest;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Handler;
import android.util.Base64;
import android.util.Log;
import android.view.MotionEvent;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;

public class MainActivity extends AppCompatActivity {

    // UI Elements
    private TextView tvYourId, tvYourPassword;
    private EditText etPartnerId, etPartnerPassword;
    private Button btnCopyCredentials, btnConnect;
    private ImageView ivPartnerScreen;
    
    // Network variables
    private ServerSocket serverSocket;
    private Socket clientSocket;
    private DataInputStream inputStream;
    private DataOutputStream outputStream;
    
    // Connection variables
    private boolean isServer = false;
    private boolean isConnected = false;
    private boolean streaming = false;
    
    // Credentials
    private String uriId;
    private String password;
    private SecretKey secretKey;
    
    // Thread pool
    private ExecutorService executorService = Executors.newFixedThreadPool(4);
    
    // Handler for UI updates
    private Handler handler = new Handler();
    
    // Screen dimensions
    private int screenWidth, screenHeight;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        // Request permissions
        requestPermissions();
        
        // Initialize UI
        initUI();
        
        // Generate credentials
        generateCredentials();
        
        // Start server automatically
        startServer();
    }
    
    private void requestPermissions() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.INTERNET) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.INTERNET}, 1);
        }
    }
    
    private void initUI() {
        tvYourId = findViewById(R.id.tvYourId);
        tvYourPassword = findViewById(R.id.tvYourPassword);
        etPartnerId = findViewById(R.id.etPartnerId);
        etPartnerPassword = findViewById(R.id.etPartnerPassword);
        btnCopyCredentials = findViewById(R.id.btnCopyCredentials);
        btnConnect = findViewById(R.id.btnConnect);
        ivPartnerScreen = findViewById(R.id.ivPartnerScreen);
        
        // Get screen dimensions
        screenWidth = getResources().getDisplayMetrics().widthPixels;
        screenHeight = getResources().getDisplayMetrics().heightPixels;
        
        btnCopyCredentials.setOnClickListener(v -> copyCredentials());
        btnConnect.setOnClickListener(v -> connectToPartner());
        
        // Setup touch listener for remote control
        ivPartnerScreen.setOnTouchListener((v, event) -> {
            if (!isConnected) return false;
            
            float x = event.getX();
            float y = event.getY();
            
            // Normalize coordinates (0-1)
            float normalizedX = x / ivPartnerScreen.getWidth();
            float normalizedY = y / ivPartnerScreen.getHeight();
            
            // Send touch event to partner
            sendTouchEvent(normalizedX, normalizedY, event.getAction());
            
            return true;
        });
    }
    
    private void generateCredentials() {
        Random random = new Random();
        uriId = String.valueOf(100000 + random.nextInt(900000));
        password = String.valueOf(1000 + random.nextInt(9000));
        
        try {
            KeyGenerator keyGen = KeyGenerator.getInstance("AES");
            keyGen.init(128);
            secretKey = keyGen.generateKey();
        } catch (Exception e) {
            e.printStackTrace();
        }
        
        // Update UI
        tvYourId.setText("Your ID: " + uriId);
        tvYourPassword.setText("Password: " + password);
    }
    
    private void copyCredentials() {
        ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        clipboard.setText("ID: " + uriId + "\nPassword: " + password);
        Toast.makeText(this, "Credentials copied to clipboard", Toast.LENGTH_SHORT).show();
    }
    
    private void startServer() {
        executorService.execute(() -> {
            try {
                serverSocket = new ServerSocket(5555);
                isServer = true;
                
                runOnUiThread(() -> Toast.makeText(MainActivity.this, 
                    "Server started - Waiting for connection...", Toast.LENGTH_SHORT).show());
                
                clientSocket = serverSocket.accept();
                inputStream = new DataInputStream(clientSocket.getInputStream());
                outputStream = new DataOutputStream(clientSocket.getOutputStream());
                
                // Verify password
                String receivedPassword = inputStream.readUTF();
                if (!receivedPassword.equals(password)) {
                    clientSocket.close();
                    runOnUiThread(() -> Toast.makeText(MainActivity.this, 
                        "Invalid password from client", Toast.LENGTH_SHORT).show());
                    return;
                }
                
                // Send encryption key
                outputStream.write(secretKey.getEncoded());
                outputStream.flush();
                
                isConnected = true;
                streaming = true;
                
                runOnUiThread(() -> {
                    Toast.makeText(MainActivity.this, "Client connected", Toast.LENGTH_SHORT).show();
                    btnConnect.setText("Connected");
                    btnConnect.setEnabled(false);
                });
                
                // Start receiving screen
                receiveScreen();
                
            } catch (IOException e) {
                e.printStackTrace();
                runOnUiThread(() -> Toast.makeText(MainActivity.this, 
                    "Server error: " + e.getMessage(), Toast.LENGTH_SHORT).show());
            }
        });
    }
    
    private void connectToPartner() {
        String partnerId = etPartnerId.getText().toString();
        String partnerPassword = etPartnerPassword.getText().toString();
        
        if (partnerId.isEmpty() || partnerPassword.isEmpty()) {
            Toast.makeText(this, "Please enter both ID and password", Toast.LENGTH_SHORT).show();
            return;
        }
        
        executorService.execute(() -> {
            try {
                clientSocket = new Socket(partnerId, 5555);
                outputStream = new DataOutputStream(clientSocket.getOutputStream());
                inputStream = new DataInputStream(clientSocket.getInputStream());
                
                // Send password
                outputStream.writeUTF(partnerPassword);
                outputStream.flush();
                
                // Receive encryption key
                byte[] keyBytes = new byte[16];
                inputStream.readFully(keyBytes);
                secretKey = new SecretKeySpec(keyBytes, "AES");
                
                isConnected = true;
                streaming = true;
                
                runOnUiThread(() -> {
                    Toast.makeText(MainActivity.this, "Connected to partner", Toast.LENGTH_SHORT).show();
                    btnConnect.setText("Connected");
                    btnConnect.setEnabled(false);
                });
                
                // Start receiving screen
                receiveScreen();
                
            } catch (IOException e) {
                e.printStackTrace();
                runOnUiThread(() -> Toast.makeText(MainActivity.this, 
                    "Connection failed: " + e.getMessage(), Toast.LENGTH_SHORT).show());
            }
        });
    }
    
    private void receiveScreen() {
        while (streaming && isConnected) {
            try {
                // Read image size
                int imageSize = inputStream.readInt();
                byte[] imageBytes = new byte[imageSize];
                
                // Read image data
                inputStream.readFully(imageBytes);
                
                // Decrypt if needed (simplified for example)
                // byte[] decryptedBytes = decrypt(imageBytes);
                byte[] decryptedBytes = imageBytes;
                
                // Convert to bitmap
                Bitmap bitmap = BitmapFactory.decodeByteArray(decryptedBytes, 0, decryptedBytes.length);
                
                // Update UI on main thread
                handler.post(() -> ivPartnerScreen.setImageBitmap(bitmap));
                
            } catch (IOException e) {
                e.printStackTrace();
                streaming = false;
                isConnected = false;
                runOnUiThread(() -> Toast.makeText(MainActivity.this, 
                    "Connection lost", Toast.LENGTH_SHORT).show());
            }
        }
    }
    
    private void sendTouchEvent(float x, float y, int action) {
        if (!isConnected) return;
        
        executorService.execute(() -> {
            try {
                // Send touch coordinates and action
                outputStream.writeFloat(x);
                outputStream.writeFloat(y);
                outputStream.writeInt(action);
                outputStream.flush();
            } catch (IOException e) {
                e.printStackTrace();
            }
        });
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        streaming = false;
        isConnected = false;
        
        try {
            if (clientSocket != null) clientSocket.close();
            if (serverSocket != null) serverSocket.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
        
        executorService.shutdown();
    }
}
