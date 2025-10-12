// BluetoothDiscoveryFragment.java
package com.example.vroomvroom;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.DialogFragment;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Bluetooth Discovery Fragment that matches the provided XML layout
 */
public class BluetoothDiscoveryFragment extends DialogFragment {
    private static final String TAG = "BluetoothDiscovery";

    private BluetoothAdapter bluetoothAdapter;
    private final List<BluetoothDevice> deviceList = new ArrayList<>();

    // UI Components
    private LinearLayout deviceListContainer;
    private TextView statusText;
    private Button scanButton;
    private Button cancelButton;

    private boolean isScanning = false;
    private BluetoothDevice selectedDevice = null;

    // Communication interface
    public interface BluetoothDiscoveryListener {
        void onDeviceSelected(BluetoothDevice device);
        void onDiscoveryCancelled();
        void onDiscoveryRefreshed();
        void onPermissionDenied();
        void onBluetoothDisabled();
    }

    private BluetoothDiscoveryListener discoveryListener;

    // BroadcastReceiver for device discovery
    private final BroadcastReceiver discoveryReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String action = intent.getAction();

            if (BluetoothDevice.ACTION_FOUND.equals(action)) {
                BluetoothDevice device = intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE);
                if (device != null) {
                    addDevice(device);
                }
            } else if (BluetoothAdapter.ACTION_DISCOVERY_FINISHED.equals(action)) {
                onDiscoveryFinished();
            }
        }
    };

    public static BluetoothDiscoveryFragment newInstance() {
        return new BluetoothDiscoveryFragment();
    }

    @Override
    public void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Set up communication with parent activity
        if (getActivity() instanceof MainActivity) {
            discoveryListener = new BluetoothDiscoveryListener() {
                @Override
                public void onDeviceSelected(BluetoothDevice device) {
                    ((MainActivity) getActivity()).handleDeviceSelected(device);
                }

                @Override
                public void onDiscoveryCancelled() {
                    ((MainActivity) getActivity()).handleDiscoveryCancelled();
                }

                @Override
                public void onDiscoveryRefreshed() {
                    ((MainActivity) getActivity()).handleDiscoveryRefreshed();
                }

                @Override
                public void onPermissionDenied() {
                    ((MainActivity) getActivity()).handlePermissionDenied();
                }

                @Override
                public void onBluetoothDisabled() {
                    ((MainActivity) getActivity()).handleBluetoothDisabled();
                }
            };
        }

        bluetoothAdapter = BluetoothAdapter.getDefaultAdapter();
        if (bluetoothAdapter == null) {
            showError("Bluetooth not supported");
            dismiss();
            return;
        }

        if (!bluetoothAdapter.isEnabled()) {
            showError("Please enable Bluetooth");
            if (discoveryListener != null) {
                discoveryListener.onBluetoothDisabled();
            }
            dismiss();
            return;
        }
    }

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        return inflater.inflate(R.layout.dialog_bluetooth_discovery, container, false);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);

        initViews(view);
        setupListeners();
        registerReceiver();
        loadDevices();
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        stopDiscovery();
        unregisterReceiver();
    }

    private void initViews(View view) {
        deviceListContainer = view.findViewById(R.id.device_list_container);
        statusText = view.findViewById(R.id.status_text);
        scanButton = view.findViewById(R.id.scan_button);
        cancelButton = view.findViewById(R.id.cancel_button);

        statusText.setText("Ready to scan");
    }

    private void setupListeners() {
        scanButton.setOnClickListener(v -> {
            if (isScanning) {
                stopDiscovery();
            } else {
                startDiscovery();
                if (discoveryListener != null) {
                    discoveryListener.onDiscoveryRefreshed();
                }
            }
        });

        cancelButton.setOnClickListener(v -> {
            if (discoveryListener != null) {
                discoveryListener.onDiscoveryCancelled();
            }
            dismiss();
        });
    }

    private void registerReceiver() {
        IntentFilter filter = new IntentFilter();
        filter.addAction(BluetoothDevice.ACTION_FOUND);
        filter.addAction(BluetoothAdapter.ACTION_DISCOVERY_FINISHED);

        if (getActivity() != null) {
            getActivity().registerReceiver(discoveryReceiver, filter);
        }
    }

    private void unregisterReceiver() {
        try {
            if (getActivity() != null) {
                getActivity().unregisterReceiver(discoveryReceiver);
            }
        } catch (IllegalArgumentException e) {
            // Receiver was not registered
            Log.d(TAG, "Receiver was not registered");
        }
    }

    private void loadDevices() {
        deviceList.clear();
        deviceListContainer.removeAllViews();

        try {
            // Load paired devices first
            Set<BluetoothDevice> pairedDevices = bluetoothAdapter.getBondedDevices();
            if (pairedDevices != null && !pairedDevices.isEmpty()) {
                for (BluetoothDevice device : pairedDevices) {
                    deviceList.add(device);
                    addDeviceToUI(device, true);
                }
                updateStatus("Found " + pairedDevices.size() + " paired device(s). Tap 'Start Scan' to find more.");
            } else {
                updateStatus("No paired devices found. Tap 'Start Scan' to discover devices.");
            }

        } catch (SecurityException e) {
            Log.e(TAG, "Permission error loading devices", e);
            showError("Permission denied");
            if (discoveryListener != null) {
                discoveryListener.onPermissionDenied();
            }
        }
    }

    private void startDiscovery() {
        try {
            // Cancel any ongoing discovery first
            if (bluetoothAdapter.isDiscovering()) {
                bluetoothAdapter.cancelDiscovery();
            }

            // Clear discovered devices but keep paired ones
            List<BluetoothDevice> pairedDevices = new ArrayList<>();
            for (BluetoothDevice device : deviceList) {
                try {
                    if (bluetoothAdapter.getBondedDevices().contains(device)) {
                        pairedDevices.add(device);
                    }
                } catch (SecurityException e) {
                    // Skip this device
                }
            }

            deviceList.clear();
            deviceList.addAll(pairedDevices);
            refreshDeviceList();

            boolean started = bluetoothAdapter.startDiscovery();
            if (started) {
                isScanning = true;
                updateScanButton();
                updateStatus("Scanning for devices... Make sure your device is in pairing mode.");
                Log.d(TAG, "Discovery started successfully");
            } else {
                showError("Failed to start scan");
                Log.e(TAG, "Failed to start discovery");
            }

        } catch (SecurityException e) {
            Log.e(TAG, "Permission error starting discovery", e);
            showError("Permission denied");
            if (discoveryListener != null) {
                discoveryListener.onPermissionDenied();
            }
        }
    }

    private void stopDiscovery() {
        try {
            if (bluetoothAdapter.isDiscovering()) {
                bluetoothAdapter.cancelDiscovery();
                Log.d(TAG, "Discovery cancelled");
            }
        } catch (SecurityException e) {
            Log.e(TAG, "Permission error stopping discovery", e);
        }

        isScanning = false;
        updateScanButton();
        updateStatus("Scan stopped. Found " + deviceList.size() + " device(s) total.");
    }

    private void onDiscoveryFinished() {
        isScanning = false;
        updateScanButton();
        int totalDevices = deviceList.size();
        updateStatus("Scan complete. Found " + totalDevices + " device(s). Tap any device to connect.");
        Log.d(TAG, "Discovery finished, found " + totalDevices + " devices");
    }

    private void addDevice(BluetoothDevice device) {
        // Skip if already in list
        for (BluetoothDevice existing : deviceList) {
            try {
                if (existing.getAddress().equals(device.getAddress())) {
                    Log.d(TAG, "Device already in list: " + device.getAddress());
                    return;
                }
            } catch (SecurityException e) {
                continue;
            }
        }

        deviceList.add(device);
        addDeviceToUI(device, false);
        updateStatus("Scanning... Found " + deviceList.size() + " device(s)");

        try {
            Log.d(TAG, "New device added: " + device.getName() + " (" + device.getAddress() + ")");
        } catch (SecurityException e) {
            Log.d(TAG, "New device added: " + device.getAddress());
        }
    }

    private void refreshDeviceList() {
        deviceListContainer.removeAllViews();

        for (BluetoothDevice device : deviceList) {
            boolean isPaired = false;
            try {
                isPaired = bluetoothAdapter.getBondedDevices().contains(device);
            } catch (SecurityException e) {
                // Assume not paired
            }
            addDeviceToUI(device, isPaired);
        }
    }

    private void addDeviceToUI(BluetoothDevice device, boolean isPaired) {
        LinearLayout deviceItem = createDeviceView(device, isPaired);
        deviceItem.setOnClickListener(v -> selectDevice(device));
        deviceListContainer.addView(deviceItem);
    }

    private LinearLayout createDeviceView(BluetoothDevice device, boolean isPaired) {
        LinearLayout container = new LinearLayout(getContext());
        container.setOrientation(LinearLayout.VERTICAL);
        container.setPadding(16, 12, 16, 12);

        // Different background colors for paired and discovered devices
        container.setBackgroundColor(isPaired ? 0xFFE8F5E8 : 0xFFF8F8F8);

        // Make it look clickable
        container.setClickable(true);
        container.setFocusable(true);

        // Add margin
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 0, 0, 8);
        container.setLayoutParams(params);

        // Device name
        TextView nameView = new TextView(getContext());
        try {
            String name = device.getName();
            nameView.setText(name != null && !name.trim().isEmpty() ? name : "Unknown Device");
        } catch (SecurityException e) {
            nameView.setText("Unknown Device");
        }
        nameView.setTextSize(16);
        nameView.setTextColor(0xFF333333);
        if (isPaired) {
            nameView.setTypeface(nameView.getTypeface(), android.graphics.Typeface.BOLD);
        }

        // Device address
        TextView addressView = new TextView(getContext());
        try {
            addressView.setText(device.getAddress());
        } catch (SecurityException e) {
            addressView.setText("Unknown Address");
        }
        addressView.setTextSize(12);
        addressView.setTextColor(0xFF666666);

        container.addView(nameView);
        container.addView(addressView);

        // Status indicator
        TextView statusView = new TextView(getContext());
        statusView.setTextSize(10);
        if (isPaired) {
            statusView.setText("✓ Paired");
            statusView.setTextColor(0xFF4CAF50);
        } else {
            statusView.setText("Available");
            statusView.setTextColor(0xFF2196F3);
        }
        container.addView(statusView);

        return container;
    }

    private void selectDevice(BluetoothDevice device) {
        selectedDevice = device;

        try {
            String deviceName = device.getName();
            String displayName = (deviceName != null && !deviceName.trim().isEmpty()) ? deviceName : device.getAddress();
            Toast.makeText(getContext(), "Connecting to: " + displayName, Toast.LENGTH_SHORT).show();
            Log.d(TAG, "Device selected: " + displayName);
        } catch (SecurityException e) {
            Toast.makeText(getContext(), "Connecting to selected device", Toast.LENGTH_SHORT).show();
            Log.d(TAG, "Device selected: " + device.getAddress());
        }

        // Stop discovery
        stopDiscovery();

        // Notify MainActivity and dismiss
        if (discoveryListener != null) {
            discoveryListener.onDeviceSelected(device);
        }
        dismiss();
    }

    private void updateScanButton() {
        scanButton.setText(isScanning ? "Stop Scan" : "Start Scan");
        scanButton.setEnabled(true);
    }

    private void updateStatus(String message) {
        statusText.setText(message);
        Log.d(TAG, "Status: " + message);
    }

    private void showError(String message) {
        Toast.makeText(getContext(), message, Toast.LENGTH_LONG).show();
        Log.e(TAG, "Error: " + message);
    }

    @Override
    public void onResume() {
        super.onResume();
        // Check if Bluetooth is still enabled
        if (bluetoothAdapter != null && !bluetoothAdapter.isEnabled()) {
            if (discoveryListener != null) {
                discoveryListener.onBluetoothDisabled();
            }
            dismiss();
        }
    }
}