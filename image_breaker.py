from google import genai
# This script uses Google Gemini Pro Vision to analyze an image and generate a detailed context description.
from PIL import Image
import os
from pathlib import Path

def load_api_key():
    """Load API key from API_KEY.txt file"""
    with open('API_KEY.txt', 'r') as file:
        return file.read().strip()

def analyze_image(image_path):
    """Analyze image using Gemini Pro Vision and generate context"""
    # Configure the API
    api_key = load_api_key()
    client = genai.Client(api_key=api_key)
    
    # Load and process the image
    image = Image.open(image_path)
    
    # Generate context prompt
    prompt = """Analyze this image in detail and provide comprehensive context including:
    1. What is shown in the image (objects, people, scenes)
    2. The overall structure and layout
    3. Key components and their relationships
    4. Any text or labels visible
    5. Technical details if it's a diagram or technical image
    6. Purpose or function if apparent
    
    Provide a detailed description that would help someone understand the image without seeing it."""
    
    # Generate response
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=[prompt, image]
    )
    return response.text

def process_all_images():
    """Process all images in downloads folder and save contexts"""
    downloads_folder = Path("downloads")
    
    if not downloads_folder.exists():
        print("Downloads folder not found!")
        return
    
    # Supported image extensions
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp'}
    
    # Find all image files
    image_files = []
    for root, dirs, files in os.walk(downloads_folder):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in image_extensions:
                image_files.append(file_path)
    
    if not image_files:
        print("No image files found in downloads folder!")
        return
    
    print(f"Found {len(image_files)} image files to process")
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Open output file for writing all contexts in data folder
    with open('data/all_images_context.txt', 'w', encoding='utf-8') as output_file:
        output_file.write("=== IMAGE ANALYSIS RESULTS ===\n\n")
        
        for i, image_path in enumerate(image_files, 1):
            print(f"Processing image {i}/{len(image_files)}: {image_path}")
            
            try:
                # Analyze the image
                context = analyze_image(image_path)
                
                # Write to file with clear separation
                output_file.write(f"IMAGE {i}: {image_path}\n")
                output_file.write("="*50 + "\n")
                output_file.write(context)
                output_file.write("\n\n" + "="*50 + "\n\n")
                
                print(f"  -> Analysis complete for {image_path.name}")
                
            except Exception as e:
                error_msg = f"Error analyzing {image_path}: {str(e)}"
                print(f"  -> {error_msg}")
                
                # Write error to file too
                output_file.write(f"IMAGE {i}: {image_path}\n")
                output_file.write("="*50 + "\n")
                output_file.write(f"ERROR: {error_msg}")
                output_file.write("\n\n" + "="*50 + "\n\n")
    
    print(f"\nAll image contexts saved to 'data/all_images_context.txt'")

def main():
    """Main function to process all images in downloads folder"""
    try:
        process_all_images()
        print("Image processing complete!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
