#!/usr/bin/env python3
"""
Bluetooth Chat Server (RPi ↔ Android)
------------------------------------
- Uses RFCOMM (SPP)
- Integrates BTMessageMapper for message formatting/parsing
- Just communicates between RPi and Android via console input/output
"""

from bluetooth import *
import threading
import sys
import signal
import logging
from bt_message_mapper import BTMessageMapper   # 👈 Import mapper

# =============================================================================
# Setup
# =============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BTServer")

running = True


def signal_handler(sig, frame):
    global running
    print("\n[RPi] Shutting down server...")
    running = False
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


# =============================================================================
# Chat Session Handler
# =============================================================================
def chat_session(client_sock, client_info):
    """Handle one chat session with Android"""
    print(f"[RPi] Connected to {client_info}")
    stop_flag = [False]

    # -------------------------------
    # Receiver Thread
    # -------------------------------
    def receive_messages(sock, stop_flag):
        while not stop_flag[0]:
            try:
                data = sock.recv(1024).decode("utf-8")
                if not data:
                    print("\n[Android disconnected]")
                    stop_flag[0] = True
                    break

                msg = data.strip()
                if msg.lower() in ["exit", "quit"]:
                    print("\n[Android ended the chat]")
                    stop_flag[0] = True
                    break

                # Parse incoming message using mapper
                parsed = BTMessageMapper.parse_android_message(msg)
                print(f"\n[Android → RPi] Raw: {msg}")
                print(f"[Android → RPi] Parsed: {parsed}")

            except OSError:
                print("\n[Android connection lost]")
                stop_flag[0] = True
                break
            except Exception as e:
                logger.warning(f"[Receiver] Error: {e}")

    recv_thread = threading.Thread(target=receive_messages, args=(client_sock, stop_flag))
    recv_thread.daemon = True
    recv_thread.start()

    # -------------------------------
    # Sending Loop (RPi → Android)
    # -------------------------------
    try:
        while not stop_flag[0]:
            msg = input("[RPi] > ").strip()

            if not msg:
                continue

            # Allow user to type “exit” to end session
            if msg.lower() in ["exit", "quit"]:
                try:
                    client_sock.send("[RPi disconnected]".encode("utf-8"))
                except:
                    pass
                print("[RPi] Chat ended.")
                stop_flag[0] = True
                break

            # --- Demonstrate Mapper Integration ---
            # Examples:
            #   robot 5 10 N         → "ROBOT, 5, 10, N"
            #   object 3 15 8 E      → "OBJECT3, 15, 8, E"
            #   target 1 15          → "TARGET, 1, 15"
            #   task 8               → "WEEK8_TASK_DONE"
            #   raw hello world      → "hello world" (send raw)

            parts = msg.split()
            if len(parts) == 0:
                continue

            try:
                cmd = parts[0].lower()
                if cmd == "robot" and len(parts) == 4:
                    mapped_msg = BTMessageMapper.format_robot_position(
                        int(parts[1]), int(parts[2]), parts[3].upper()
                    )
                elif cmd == "object" and len(parts) == 5:
                    mapped_msg = BTMessageMapper.format_object_position(
                        int(parts[1]), int(parts[2]), int(parts[3]), parts[4].upper()
                    )
                elif cmd == "target" and len(parts) == 3:
                    mapped_msg = BTMessageMapper.format_target(
                        int(parts[1]), int(parts[2])
                    )
                elif cmd == "task" and len(parts) == 2:
                    mapped_msg = BTMessageMapper.format_task_done(int(parts[1]))
                elif cmd == "raw":
                    mapped_msg = " ".join(parts[1:])
                else:
                    mapped_msg = msg  # fallback raw

                client_sock.send(mapped_msg.encode("utf-8"))
                print(f"[RPi → Android] Sent: {mapped_msg}")

            except Exception as e:
                logger.warning(f"[Sender] Invalid command format: {e}")

    except KeyboardInterrupt:
        print("\n[RPi] Chat interrupted")
        stop_flag[0] = True

    finally:
        try:
            client_sock.shutdown(2)
        except:
            pass
        client_sock.close()
        print("[RPi] Session closed\n")


# =============================================================================
# Main Server Loop
# =============================================================================
def main():
    global running
    server_sock = BluetoothSocket(RFCOMM)
    server_sock.bind(("", 1))   # RFCOMM channel 1
    server_sock.listen(1)

    port = server_sock.getsockname()[1]
    uuid = "00001101-0000-1000-8000-00805F9B34FB"

    print("[RPi] Waiting for paired Android to connect (SPP advertised)...")
    print(f"[RPi] Chat server running on RFCOMM channel {port}")
    print("[RPi] Press CTRL+C to quit.\n")

    try:
        while running:
            print("[RPi] Waiting for connection...")
            try:
                client_sock, client_info = server_sock.accept()
                chat_session(client_sock, client_info)
            except OSError:
                break
    finally:
        server_sock.close()
        print("[RPi] Server shut down")


if __name__ == "__main__":
    main()

