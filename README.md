# PDF Heading Extractor - Adobe Hackathon Submission

## Approach

Our solution uses a font-based analysis approach combined with style detection to identify document structure. The system first analyzes the entire PDF to establish a baseline body text font size, then applies hierarchical rules to classify headings into H1, H2, and H3 levels.

The algorithm works in three phases: (1) Font size analysis across all pages to determine the most common size as body text baseline, (2) Text extraction with font properties and style flags, and (3) Rule-based classification where larger fonts become H1, medium-large bold text becomes H2, and medium bold text becomes H3. We also implement robust filtering to eliminate false positives like page numbers and fragmented text.

For title extraction, we prioritize PDF metadata first, then fall back to finding the largest text on the first page. This dual approach ensures reliable title detection across various PDF types and creation methods.

## Models/Libraries Used

- **PyMuPDF (fitz)**: Primary PDF processing library for text extraction and font analysis
- **Python standard libraries**: json, os, re, collections for data processing and file handling
- **No ML models**: Solution uses rule-based approach for fast, reliable processing
