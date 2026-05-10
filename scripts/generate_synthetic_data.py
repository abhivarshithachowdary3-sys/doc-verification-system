"""
Generate synthetic Aadhaar-like test images for pipeline testing.
Uses Pillow — no real Aadhaar data is created.
"""

import os
import random
import string
from PIL import Image, ImageDraw, ImageFont


def random_aadhaar() -> str:
    # Not a real Aadhaar — purely synthetic 12-digit string
    return " ".join(["".join([str(random.randint(0,9)) for _ in range(4)]) for _ in range(3)])

def random_name() -> str:
    first = random.choice(["Rahul","Priya","Amit","Sunita","Vikram","Anjali","Rohan","Meera"])
    last  = random.choice(["Sharma","Verma","Patel","Gupta","Singh","Reddy","Nair","Iyer"])
    return f"{first} {last}"

def random_dob() -> str:
    y = random.randint(1965, 2000)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{d:02d}/{m:02d}/{y}"

def generate_aadhaar_image(output_path: str):
    img = Image.new("RGB", (856, 540), color="#f5f5f0")
    draw = ImageDraw.Draw(img)

    # Header bar
    draw.rectangle([0, 0, 856, 80], fill="#1a2e4a")
    draw.text((30, 20), "Government of India", fill="white")
    draw.text((30, 45), "Unique Identification Authority of India", fill="#93c5fd")

    # Aadhaar label
    draw.text((600, 20), "आधार", fill="#f97316")
    draw.text((600, 50), "AADHAAR", fill="#f97316")

    # Body content
    name = random_name()
    dob  = random_dob()
    uid  = random_aadhaar()
    gender = random.choice(["MALE", "FEMALE"])

    draw.text((30, 110), f"Name:    {name}", fill="#1a202c")
    draw.text((30, 150), f"DOB:     {dob}", fill="#1a202c")
    draw.text((30, 190), f"Gender:  {gender}", fill="#1a202c")
    draw.text((30, 240), f"{uid}", fill="#1a202c")

    # Footer
    draw.rectangle([0, 480, 856, 540], fill="#e5e7eb")
    draw.text((30, 495), "This is a SYNTHETIC TEST document — not a real Aadhaar card", fill="#6b7280")

    img.save(output_path)
    print(f"Saved: {output_path}")
    return {"name": name, "dob": dob, "uid": uid, "gender": gender}


if __name__ == "__main__":
    os.makedirs("test_images", exist_ok=True)
    for i in range(5):
        meta = generate_aadhaar_image(f"test_images/synthetic_aadhaar_{i+1}.png")
        print(f"  → {meta}")
    print("\n✅ 5 synthetic Aadhaar test images created in test_images/")
