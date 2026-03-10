# myapp/ml_utils.py
from deepface import DeepFace

# Verhoeff Algorithm Tables for Aadhaar Validation
d = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6], [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4], [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]
p = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2], [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]
inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def validate_aadhaar_number(aadhaar_num: str) -> bool:
    """Validates Aadhaar number using the Verhoeff algorithm."""
    if len(aadhaar_num) != 12 or not aadhaar_num.isdigit():
        return False
    c = 0
    inverted_array = list(map(int, reversed(aadhaar_num)))
    for i in range(len(inverted_array)):
        c = d[c][p[i % 8][inverted_array[i]]]
    return c == 0

def verify_faces(live_image_path: str, aadhaar_image_path: str) -> bool:
    """
    Compares the face in the live photo to the face on the Aadhaar card.
    Uses DeepFace which automatically detects and crops faces before comparing.
    """
    try:
        # We use Facenet512 or VGG-Face for high accuracy
        result = DeepFace.verify(img1_path=live_image_path, 
                                 img2_path=aadhaar_image_path, 
                                 model_name="Facenet", 
                                 enforce_detection=True) # Forces it to find a face
        return result["verified"]
    except Exception as e:
        print(f"Face verification failed: {e}")
        return False