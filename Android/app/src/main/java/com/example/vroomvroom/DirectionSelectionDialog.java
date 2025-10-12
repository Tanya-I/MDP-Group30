// DirectionSelectionDialog.java
package com.example.vroomvroom;

import android.app.AlertDialog;
import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

public class DirectionSelectionDialog {

    public interface OnDirectionSelectedListener {
        void onDirectionSelected(String itemName, String direction);
        void onDirectionCancelled(String itemName);
    }

    private AlertDialog dialog;
    private OnDirectionSelectedListener listener;
    private Context context;

    public DirectionSelectionDialog(Context context) {
        this.context = context;
    }

    public void setOnDirectionSelectedListener(OnDirectionSelectedListener listener) {
        this.listener = listener;
    }

    public void showDirectionDialog(String itemName, String itemType) {
        // Create custom dialog layout
        LayoutInflater inflater = LayoutInflater.from(context);
        View dialogView = inflater.inflate(R.layout.dialog_direction_selection, null);

        // Find views
        TextView titleText = dialogView.findViewById(R.id.dialog_title);
        TextView itemText = dialogView.findViewById(R.id.dialog_item_name);
        Button northButton = dialogView.findViewById(R.id.button_north);
        Button southButton = dialogView.findViewById(R.id.button_south);
        Button eastButton = dialogView.findViewById(R.id.button_east);
        Button westButton = dialogView.findViewById(R.id.button_west);
        Button cancelButton = dialogView.findViewById(R.id.button_cancel);

        // Set dialog content
        String title = itemType.equals("ROBOT") ? "Set Robot Direction" : "Set Object Direction";
        titleText.setText(title);
        itemText.setText("Item: " + itemName);

        // Create dialog
        AlertDialog.Builder builder = new AlertDialog.Builder(context);
        builder.setView(dialogView);
        builder.setCancelable(true);

        dialog = builder.create();

        // Set up button listeners
        View.OnClickListener directionClickListener = new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String direction = "";
                if (v.getId() == R.id.button_north) {
                    direction = "N";
                } else if (v.getId() == R.id.button_south) {
                    direction = "S";
                } else if (v.getId() == R.id.button_east) {
                    direction = "E";
                } else if (v.getId() == R.id.button_west) {
                    direction = "W";
                }

                if (listener != null) {
                    listener.onDirectionSelected(itemName, direction);
                }
                dialog.dismiss();
            }
        };

        northButton.setOnClickListener(directionClickListener);
        southButton.setOnClickListener(directionClickListener);
        eastButton.setOnClickListener(directionClickListener);
        westButton.setOnClickListener(directionClickListener);

        cancelButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (listener != null) {
                    listener.onDirectionCancelled(itemName);
                }
                dialog.dismiss();
            }
        });

        // Show dialog
        dialog.show();
    }

    public void dismiss() {
        if (dialog != null && dialog.isShowing()) {
            dialog.dismiss();
        }
    }
}