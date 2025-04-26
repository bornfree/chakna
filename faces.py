import face_recognition
import cv2
import numpy as np
import sys

def extract_face_embeddings(image_path):
    # Load image using face_recognition (uses dlib internally)
    image = face_recognition.load_image_file(image_path)

    # Detect face locations
    face_locations = face_recognition.face_locations(image)

    # Compute embeddings (128-d vector per face)
    face_encodings = face_recognition.face_encodings(image, face_locations)

    print(f"Found {len(face_locations)} face(s) in the image.")

    results = []
    for (top, right, bottom, left), embedding in zip(face_locations, face_encodings):
        face_crop = image[top:bottom, left:right]
        results.append({
            "location": (top, right, bottom, left),
            "embedding": embedding.tolist(),  # convert numpy array to list
            "face_crop": face_crop  # This can be saved or sent to server
        })

    return results

# Example usage
if __name__ == "__main__":
    image_path = sys.argv[1]
    results = extract_face_embeddings(image_path)

    for i, res in enumerate(results):
        print(f"Face {i+1} embedding (first 5 dims): {res['embedding'][:5]}")

