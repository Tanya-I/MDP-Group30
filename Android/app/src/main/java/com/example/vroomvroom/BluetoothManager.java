// BluetoothManager.java
package com.example.vroomvroom;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Handler;
import android.util.Log;
import androidx.localbroadcastmanager.content.LocalBroadcastManager;

import java.util.UUID;

public class BluetoothManager {
    private static final String TAG = "BluetoothManager";
    private static final UUID BLUETOOTH_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");
    private static final int MAX_RECONNECT_ATTEMPTS = 10;
    private static final long RECONNECT_DELAY_MS = 4000; // 4 sec

    // Bluetooth components
    private BluetoothAdapter bluetoothAdapter;
    private BluetoothConnectionService bluetoothService;
    private BroadcastReceiver bluetoothConnectionReceiver;
    private Context context;

    // Connection state
    private boolean isConnected = false;
    private String connectedDeviceName = "";
    private String lastConnectedDeviceName = ""; // Store the last device name separately
    private BluetoothDevice lastConnectedDevice = null;

    // Auto-reconnection state
    private Handler reconnectHandler = new Handler();
    private boolean isReconnecting = false;
    private int reconnectAttempts = 0;
    private boolean autoReconnectEnabled = true;

    // Listener interface for communicating with UI
    public interface BluetoothListener {
        void onConnectionStatusChanged(boolean connected, String deviceName);
        void onConnectionAttemptStarted(String deviceName);
        void onConnectionFailed(String errorMessage);
        void onMessageReceived(String message);
        void onStatusMessage(String message);
        void onPermissionDenied();
        void onBluetoothDisabled();
    }

    private BluetoothListener listener;

    public BluetoothManager(Context context) {
        this.context = context;
        this.bluetoothAdapter = BluetoothAdapter.getDefaultAdapter();
        setupBluetoothConnectionReceiver();
    }

    public void setListener(BluetoothListener listener) {
        this.listener = listener;
    }

    public boolean isBluetoothSupported() {
        return bluetoothAdapter != null;
    }

    public boolean isBluetoothEnabled() {
        return bluetoothAdapter != null && bluetoothAdapter.isEnabled();
    }

    public boolean isConnected() {
        return isConnected;
    }

    public String getConnectedDeviceName() {
        return connectedDeviceName;
    }

    public boolean isAutoReconnectEnabled() {
        return autoReconnectEnabled;
    }

    public void setAutoReconnectEnabled(boolean enabled) {
        autoReconnectEnabled = enabled;
        if (listener != null) {
            listener.onStatusMessage("Auto-reconnection " + (enabled ? "enabled" : "disabled"));
        }
        if (!enabled) {
            cancelReconnectionAttempts();
        }
    }

    public void connectToDevice(BluetoothDevice device) {
        if (!isBluetoothEnabled()) {
            if (listener != null) {
                listener.onBluetoothDisabled();
            }
            return;
        }

        // Get and store device name before connection attempt
        String deviceName = getDeviceName(device);
        connectedDeviceName = deviceName;

        if (listener != null) {
            listener.onConnectionAttemptStarted(deviceName);
        }

        // Cancel any pending reconnection attempts
        cancelReconnectionAttempts();

        // Initialize fresh Bluetooth service
        createFreshBluetoothService();

        // Start actual Bluetooth connection
        try {
            bluetoothService.startClientThread(device, BLUETOOTH_UUID);
            if (listener != null) {
                listener.onStatusMessage("Connection attempt started...");
            }
        } catch (Exception e) {
            Log.e(TAG, "Error starting Bluetooth connection", e);
            handleConnectionFailure("Failed to start connection: " + e.getMessage());
        }
    }

    public void disconnect() {
        // Store the device name before clearing connection state
        String deviceNameForMessage = isConnected ? connectedDeviceName : lastConnectedDeviceName;

        if (listener != null) {
            listener.onStatusMessage("Manually disconnecting from " + deviceNameForMessage + "...");
        }

        // Cancel auto-reconnection when user manually disconnects
        cancelReconnectionAttempts();

        if (bluetoothService != null) {
            bluetoothService.disconnect();
        }

        isConnected = false;
        connectedDeviceName = "";

        if (listener != null) {
            listener.onConnectionStatusChanged(false, "");
            listener.onStatusMessage("Disconnected from bluetooth device");
        }
    }

    public void sendMessage(String message) {
        if (bluetoothService != null && isConnected) {
            try {
                byte[] bytes = message.getBytes();
                bluetoothService.write(bytes);
                if (listener != null) {
                    listener.onStatusMessage("Sent: " + message);
                }
                Log.d(TAG, "Sent message: " + message);
            } catch (Exception e) {
                Log.e(TAG, "Error sending message", e);
                if (listener != null) {
                    listener.onStatusMessage("Failed to send message: " + e.getMessage());
                }
            }
        } else {
            if (listener != null) {
                listener.onStatusMessage("Cannot send message - not connected to device");
            }
            Log.w(TAG, "Attempted to send message but not connected");
        }
    }

    public void cleanup() {
        // Stop auto-reconnection
        autoReconnectEnabled = false;
        reconnectHandler.removeCallbacksAndMessages(null);

        // Unregister broadcast receivers
        if (bluetoothConnectionReceiver != null) {
            try {
                LocalBroadcastManager.getInstance(context).unregisterReceiver(bluetoothConnectionReceiver);
            } catch (IllegalArgumentException e) {
                // Receiver was not registered
            }
        }

        // Clean up Bluetooth service
        if (bluetoothService != null) {
            bluetoothService.disconnect();
        }
    }

    private void createFreshBluetoothService() {
        // Clean up old service
        if (bluetoothService != null) {
            bluetoothService.disconnect();
        }

        // Brief delay to ensure cleanup
        try {
            Thread.sleep(100);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        // Create new service
        bluetoothService = new BluetoothConnectionService(context);
    }

    private void setupBluetoothConnectionReceiver() {
        bluetoothConnectionReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                String status = intent.getStringExtra("Status");
                BluetoothDevice device = intent.getParcelableExtra("Device");

                if (status != null) {
                    handleBluetoothConnectionStatus(status, device);
                }
            }
        };

        // Register the receiver
        IntentFilter filter = new IntentFilter("ConnectionStatus");
        LocalBroadcastManager.getInstance(context).registerReceiver(bluetoothConnectionReceiver, filter);

        // Also register for incoming messages
        BroadcastReceiver messageReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                String message = intent.getStringExtra("receivedMessage");
                if (message != null && listener != null) {
                    listener.onMessageReceived(message);
                }
            }
        };

        IntentFilter messageFilter = new IntentFilter("incomingMessage");
        LocalBroadcastManager.getInstance(context).registerReceiver(messageReceiver, messageFilter);
    }

    private void handleBluetoothConnectionStatus(String status, BluetoothDevice device) {
        Log.d(TAG, "Bluetooth connection status: " + status);

        switch (status) {
            case "connected":
                isConnected = true;
                isReconnecting = false;

                // Store successful connection
                lastConnectedDevice = device;
                reconnectAttempts = 0; // Reset on successful connection

                // Update device name if we have a better one from the device
                if (device != null) {
                    String deviceName = getDeviceName(device);
                    if (!deviceName.equals("Unknown Device")) {
                        connectedDeviceName = deviceName;
                    }
                }

                // Store the last connected device name
                lastConnectedDeviceName = connectedDeviceName;

                if (listener != null) {
                    listener.onConnectionStatusChanged(true, connectedDeviceName);
                    listener.onStatusMessage("Successfully connected to " + connectedDeviceName);
                }
                break;

            case "disconnected":
            case "failed":
                isConnected = false;
                // Store the current device name before clearing it
                String deviceNameForMessage = !connectedDeviceName.isEmpty() ? connectedDeviceName : lastConnectedDeviceName;
                connectedDeviceName = "";

                if (listener != null) {
                    listener.onConnectionStatusChanged(false, "");

                    if (isReconnecting) {
                        listener.onStatusMessage("Reconnection attempt failed for " + deviceNameForMessage);
                    } else {
                        listener.onStatusMessage("Disconnected from " + deviceNameForMessage);
                    }
                }

                // Only auto-reconnect if enabled, we have a device, and not already reconnecting
                if (autoReconnectEnabled && lastConnectedDevice != null &&
                        !isReconnecting && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                    scheduleReconnection();
                } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
                    if (listener != null) {
                        listener.onStatusMessage("Max reconnection attempts reached for " + lastConnectedDeviceName + ". Auto-reconnection stopped.");
                    }
                }
                break;

            default:
                Log.w(TAG, "Unknown connection status: " + status);
                if (listener != null) {
                    listener.onStatusMessage("Connection status: " + status);
                }
        }
    }

    private void scheduleReconnection() {
        if (!autoReconnectEnabled || lastConnectedDevice == null || isReconnecting) {
            return;
        }

        reconnectAttempts++;
        isReconnecting = true;

        String deviceNameForMessage = !lastConnectedDeviceName.isEmpty() ? lastConnectedDeviceName : getDeviceName(lastConnectedDevice);

        if (listener != null) {
            listener.onStatusMessage("Auto-reconnecting to " + deviceNameForMessage + "... attempt " + reconnectAttempts + "/" +
                    MAX_RECONNECT_ATTEMPTS + " in " + (RECONNECT_DELAY_MS / 1000) + " seconds");
        }

        reconnectHandler.postDelayed(() -> {
            if (autoReconnectEnabled && !isConnected && lastConnectedDevice != null) {
                String deviceName = !lastConnectedDeviceName.isEmpty() ? lastConnectedDeviceName : getDeviceName(lastConnectedDevice);

                if (listener != null) {
                    listener.onStatusMessage("Attempting reconnection to " + deviceName);
                }

                // Create fresh service and attempt connection
                createFreshBluetoothService();

                try {
                    bluetoothService.startClientThread(lastConnectedDevice, BLUETOOTH_UUID);
                } catch (Exception e) {
                    Log.e(TAG, "Reconnection attempt failed", e);
                    isReconnecting = false;
                    if (listener != null) {
                        listener.onStatusMessage("Reconnection attempt failed: " + e.getMessage());
                    }

                    // Schedule next attempt if within limits
                    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                        scheduleReconnection();
                    }
                }
            } else {
                isReconnecting = false;
            }
        }, RECONNECT_DELAY_MS);
    }

    private String getDeviceName(BluetoothDevice device) {
        if (device == null) {
            return "Unknown Device";
        }

        try {
            String name = device.getName();
            if (name != null && !name.trim().isEmpty()) {
                return name.trim();
            } else {
                // To addres case where name is null or empty
                String address = device.getAddress();
                return address != null ? address : "Unknown Device";
            }
        } catch (SecurityException e) {
            Log.w(TAG, "Security exception getting device name", e);
            return "Unknown Device";
        }
    }

    private void cancelReconnectionAttempts() {
        reconnectHandler.removeCallbacksAndMessages(null);
        reconnectAttempts = 0;
        isReconnecting = false;
        if (listener != null) {
            listener.onStatusMessage("Cancelled pending reconnection attempts");
        }
    }

    private void handleConnectionFailure(String errorMessage) {
        isConnected = false;
        isReconnecting = false;
        connectedDeviceName = "";

        if (listener != null) {
            listener.onConnectionStatusChanged(false, "");
            listener.onConnectionFailed(errorMessage);
        }
    }
}