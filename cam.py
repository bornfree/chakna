import cv2

# Open the webcam (device 0, change if you have multiple cameras)
cap = cv2.VideoCapture(0)

# Check if the webcam is opened correctly
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

# Read one frame
ret, frame = cap.read()

if ret:
    # Save the frame to a file
    filename = "first_frame.jpg"
    cv2.imwrite(filename, frame)
    print(f"First frame saved as {filename}")
else:
    print("Error: Could not read frame.")

# Release the webcam
cap.release()

