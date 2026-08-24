import serial
import time

def test_serial():
    print("Opening COM9...")
    try:
        ser = serial.Serial('COM9', 9600, timeout=1)
        ser.setDTR(False)
        time.sleep(0.05)
        ser.setDTR(True)
        ser.setRTS(True)
        print("COM9 Opened! Waiting 3 seconds for Arduino to boot...")
        time.sleep(3)
        
        print("Reading from Arduino:")
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"<- {line}")
                
        print("Sending SYSTEM_START...")
        ser.write(b"SYSTEM_START\n")
        ser.flush()
        
        print("Reading reply for 2 seconds:")
        end_time = time.time() + 2
        while time.time() < end_time:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"<- {line}")
            time.sleep(0.1)
            
        ser.close()
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_serial()
