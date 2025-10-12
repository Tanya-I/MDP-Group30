// DoubleClickHandler.java
package com.example.vroomvroom;

import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.util.Log;

public class DoubleClickHandler {

    private static final String TAG = "DoubleClickHandler";

    public interface OnClickListener {
        void onSingleClick(String itemName, String itemType);
        void onDoubleClick(String itemName, String itemType);
    }

    private static final int DOUBLE_CLICK_TIMEOUT = 300; // milliseconds

    private OnClickListener listener;
    private Handler handler;
    private boolean waitingForSecondClick = false;
    private String pendingItemName;
    private String pendingItemType;
    private Runnable pendingRunnable;

    public DoubleClickHandler() {
        handler = new Handler(Looper.getMainLooper());
    }

    public void setOnClickListener(OnClickListener listener) {
        this.listener = listener;
        Log.d(TAG, "OnClickListener set: " + (listener != null));
    }

    public View.OnClickListener createClickListener(String itemName, String itemType) {
        Log.d(TAG, "Creating click listener for: " + itemName + " (" + itemType + ")");
        return new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Log.d(TAG, "Click detected on: " + itemName);
                handleClick(itemName, itemType);
            }
        };
    }

    private void handleClick(String itemName, String itemType) {
        Log.d(TAG, "handleClick called - Item: " + itemName + ", Waiting: " + waitingForSecondClick);

        if (waitingForSecondClick && pendingItemName != null && pendingItemName.equals(itemName)) {
            // Second click detected within timeout - it's a double click
            Log.d(TAG, "Double click detected on: " + itemName);
            waitingForSecondClick = false;

            // Cancel the pending single click
            if (pendingRunnable != null) {
                handler.removeCallbacks(pendingRunnable);
                pendingRunnable = null;
            }

            if (listener != null) {
                listener.onDoubleClick(itemName, itemType);
            } else {
                Log.w(TAG, "Listener is null for double click");
            }

            // Clear pending state
            pendingItemName = null;
            pendingItemType = null;
        } else {
            // First click - wait for potential second click
            Log.d(TAG, "First click on: " + itemName + ", setting up timeout");
            waitingForSecondClick = true;
            pendingItemName = itemName;
            pendingItemType = itemType;

            // Create the runnable for single click timeout
            pendingRunnable = new Runnable() {
                @Override
                public void run() {
                    Log.d(TAG, "Single click timeout reached for: " + itemName);
                    if (waitingForSecondClick && pendingItemName != null && pendingItemName.equals(itemName)) {
                        // Timeout reached, it was a single click
                        waitingForSecondClick = false;
                        if (listener != null) {
                            listener.onSingleClick(itemName, itemType);
                        } else {
                            Log.w(TAG, "Listener is null for single click");
                        }
                        pendingItemName = null;
                        pendingItemType = null;
                        pendingRunnable = null;
                    }
                }
            };

            // Set timeout - if no second click, treat as single click
            handler.postDelayed(pendingRunnable, DOUBLE_CLICK_TIMEOUT);
        }
    }

    public void cleanup() {
        Log.d(TAG, "Cleanup called");
        if (handler != null && pendingRunnable != null) {
            handler.removeCallbacks(pendingRunnable);
        }
        waitingForSecondClick = false;
        pendingItemName = null;
        pendingItemType = null;
        pendingRunnable = null;
    }
}