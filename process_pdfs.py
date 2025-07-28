import fitz 
import json
import os
import re
from collections import Counter

def find_most_common_font_size(font_sizes):
    """Find the most common font size (body text baseline)"""
    if not font_sizes:
        return 12.0  # Default fallback
    
    font_counter = Counter(font_sizes)
    return font_counter.most_common(1)[0][0]

def clean_text(text):
    """Clean and normalize text content"""
    text = re.sub(r'\s+', ' ', text.strip())
    return text

def is_likely_heading(text):
    """Check if text content suggests it's a heading"""
    if not text or len(text.strip()) == 0:
        return False
    if len(text) > 200:
        return False
    if len(text.strip()) < 3:
        return False
    if re.match(r'^\d+$', text.strip()) or re.match(r'^[ivxlcdm]+$', text.strip().lower()):
        return False
    
    return True

def extract_title_from_pdf(doc):
    """Extract document title from metadata or first page"""
    metadata_title = doc.metadata.get('title', '').strip()
    if metadata_title:
        return clean_text(metadata_title)

    if len(doc) == 0:
        return "Untitled Document"
    
    first_page = doc[0]
    blocks = first_page.get_text("dict")["blocks"]
    
    largest_text = ""
    largest_size = 0
    
    for block in blocks:
        if "lines" in block:  # Text block
            for line in block["lines"]:
                line_text_parts = []
                max_font_size = 0
                
                for span in line["spans"]:
                    font_size = round(span["size"], 1)
                    text = span["text"]
                    line_text_parts.append(text)
                    max_font_size = max(max_font_size, font_size)
                
                full_text = clean_text("".join(line_text_parts))

                if (max_font_size > largest_size and 
                    len(full_text) > 5 and 
                    len(full_text) < 150 and
                    full_text):
                    largest_text = full_text
                    largest_size = max_font_size
    
    return largest_text if largest_text else "Untitled Document"

def analyze_pdf_structure(pdf_path):
    """
    Analyze PDF structure to extract title and headings (H1, H2, H3 only).
    Returns a dictionary with title and outline.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return {"title": "Error Loading Document", "outline": []}

    title = extract_title_from_pdf(doc)

    font_sizes = []
    
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" in block:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_size = round(span["size"], 1)
                        font_sizes.append(font_size)
    body_text_size = find_most_common_font_size(font_sizes)
    extracted_headings = []
    
    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if "lines" in block:  # Text block
                for line in block["lines"]:
                    line_text_parts = []
                    line_font_size = None
                    line_is_bold = False
                   
                    for span in line["spans"]:
                        font_size = round(span["size"], 1)
                        is_bold = bool(span["flags"] & 16)  # Bold flag
                        text = span["text"]
                        
                        line_text_parts.append(text)
                      
                        if line_font_size is None or font_size > line_font_size:
                            line_font_size = font_size
                     
                        if is_bold:
                            line_is_bold = True
            
                    full_text = "".join(line_text_parts)
                    clean_full_text = clean_text(full_text)
 
                    if not is_likely_heading(clean_full_text):
                        continue
                    
                    current_level = None
                    if line_font_size > body_text_size * 1.5:
                        current_level = "H1"
                    elif line_font_size > body_text_size * 1.2 and line_is_bold:
                        current_level = "H2"
                    elif (line_font_size > body_text_size and line_is_bold) or \
                         (line_is_bold and line_font_size >= body_text_size * 0.9):
                        current_level = "H3"
                    if current_level:
                        heading_data = {
                            "level": current_level,
                            "text": clean_full_text,
                            "page": page_num + 1
                        }
                        extracted_headings.append(heading_data)
    
    doc.close()
    
    return {
        "title": title,
        "outline": extracted_headings
    }

def process_single_pdf(input_path, output_path):
    """Process a single PDF file and save results to JSON"""
    result = analyze_pdf_structure(input_path)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Processed: {input_path} -> {output_path}")
        return True
    except Exception as e:
        print(f"Error saving {output_path}: {e}")
        return False

def process_pdfs():
    """
    Main function for Docker execution.
    Processes all PDF files in /app/input/ and saves results to /app/output/
    """
    input_dir = "/app/input"
    output_dir = "/app/output"

    os.makedirs(output_dir, exist_ok=True)

    pdf_files = []
    if os.path.exists(input_dir):
        for filename in os.listdir(input_dir):
            if filename.lower().endswith('.pdf'):
                pdf_files.append(filename)
    
    if not pdf_files:
        print("No PDF files found in /app/input/")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to process")

    successful_count = 0
    for pdf_filename in pdf_files:
        input_path = os.path.join(input_dir, pdf_filename)
        json_filename = os.path.splitext(pdf_filename)[0] + '.json'
        output_path = os.path.join(output_dir, json_filename)
        
        if process_single_pdf(input_path, output_path):
            successful_count += 1
    
    print(f"Successfully processed {successful_count}/{len(pdf_files)} PDF files")

def main():
    """Entry point - handles both command line and Docker execution"""
    import sys

    if len(sys.argv) == 1:
        # Docker execution mode
        process_pdfs()
    else:
        if len(sys.argv) < 2:
            print("Usage: python process_pdfs.py <pdf_file_path> [output_json_path]")
            print("Or run without arguments for Docker mode (processes /app/input/)")
            return
        
        pdf_file_path = sys.argv[1]
        output_json_path = sys.argv[2] if len(sys.argv) > 2 else "output.json"
        
        try:
            if process_single_pdf(pdf_file_path, output_json_path):
                with open(output_json_path, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                
                print(f"\n=== SUMMARY ===")
                print(f"Title: {result['title']}")
                print(f"Total headings found: {len(result['outline'])}")

                level_counts = {}
                for heading in result['outline']:
                    level = heading['level']
                    level_counts[level] = level_counts.get(level, 0) + 1
                
                for level in ['H1', 'H2', 'H3']:
                    if level in level_counts:
                        print(f"  {level}: {level_counts[level]}")

                if result['outline']:
                    print(f"\nFirst few headings:")
                    for i, heading in enumerate(result['outline'][:5]):
                        print(f"  {heading['level']}: {heading['text']} (Page {heading['page']})")
                    if len(result['outline']) > 5:
                        print(f"  ... and {len(result['outline']) - 5} more")
        
        except FileNotFoundError:
            print(f"Error: PDF file '{pdf_file_path}' not found.")
        except Exception as e:
            print(f"Error processing PDF: {e}")

if __name__ == "__main__":
    main()
