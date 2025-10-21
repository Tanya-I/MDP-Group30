package com.example.vroomvroom;

import android.content.Context;
import android.text.method.ScrollingMovementMethod;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

public class SwipeablePagerAdapter extends RecyclerView.Adapter<SwipeablePagerAdapter.PageViewHolder> {

    private static final int PAGE_STATUS = 0;
    private static final int PAGE_CHAT = 1;

    private Context context;
    private TextView statusTextView;
    private EditText chatEditText;
    private OnSendMessageListener sendMessageListener;

    public interface OnSendMessageListener {
        void onSendMessage(String message);
    }

    public SwipeablePagerAdapter(Context context) {
        this.context = context;
    }

    public void setOnSendMessageListener(OnSendMessageListener listener) {
        this.sendMessageListener = listener;
    }

    @Override
    public int getItemCount() {
        return 2;
    }

    @Override
    public int getItemViewType(int position) {
        return position == 0 ? PAGE_STATUS : PAGE_CHAT;
    }

    @NonNull
    @Override
    public PageViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        LayoutInflater inflater = LayoutInflater.from(context);
        View view;

        if (viewType == PAGE_STATUS) {
            view = inflater.inflate(R.layout.status_page, parent, false);
        } else {
            view = inflater.inflate(R.layout.chat_page, parent, false);
        }

        return new PageViewHolder(view, viewType);
    }

    @Override
    public void onBindViewHolder(@NonNull PageViewHolder holder, int position) {
        if (holder.viewType == PAGE_STATUS) {
            statusTextView = holder.itemView.findViewById(R.id.status_text);
            statusTextView.setMovementMethod(new ScrollingMovementMethod());
            statusTextView.setText("Status messages will appear here...");
        } else if (holder.viewType == PAGE_CHAT) {
            chatEditText = holder.itemView.findViewById(R.id.chat_input);
            Button sendButton = holder.itemView.findViewById(R.id.chat_send_button);

            sendButton.setOnClickListener(v -> {
                String message = chatEditText.getText().toString().trim();
                if (!message.isEmpty() && sendMessageListener != null) {
                    sendMessageListener.onSendMessage(message);
                    chatEditText.setText("");
                }
            });
        }
    }

    // Method to append message to status text
    public void appendStatusMessage(String msg) {
        if (statusTextView != null) {
            String oldText = statusTextView.getText().toString();
            String newText = oldText.isEmpty() ? msg : oldText + "\n" + msg;
            statusTextView.setText(newText);

            // Auto-scroll to bottom
            statusTextView.post(() -> {
                int scrollAmount = statusTextView.getLineCount() * statusTextView.getLineHeight()
                        - statusTextView.getHeight();
                if (scrollAmount > 0) {
                    statusTextView.scrollTo(0, scrollAmount);
                }
            });
        }
    }

    static class PageViewHolder extends RecyclerView.ViewHolder {
        int viewType;

        public PageViewHolder(@NonNull View itemView, int viewType) {
            super(itemView);
            this.viewType = viewType;
        }
    }
}