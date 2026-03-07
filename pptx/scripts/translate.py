#!/usr/bin/env python3
"""
Translate PowerPoint presentation while maintaining formatting.
Usage:
    python translate.py <input.pptx> <output.pptx> <target_lang> [--provider <provider>] [--skip-notes] [--terms <terms>]

Example:
    python translate.py presentation.pptx translated.pptx zh-CN
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add the current script's directory to sys.path to import inventory and replace
sys.path.append(str(Path(__file__).parent))

try:
    from inventory import extract_text_inventory, get_inventory_as_dict
    from replace import apply_replacements
except ImportError:
    print("Error: Could not import inventory or replace scripts. Ensure they are in the same directory.")
    sys.exit(1)

# Common technical terms to preserve in English
DEFAULT_PROTECTED_TERMS = [
    "NVIDIA", "AI", "Infrastructure", "Enterprise", "Bring up", "Orchestration",
    "GPU", "vGPU", "MIG", "Blackwell", "Modulus", "Isaac Sim", "Omniverse",
    "CWE", "POR", "veOmniverse", "veOV", "Sim2Real", "Dataset", "Workflow",
    "Kubernetes", "K8s", "Docker", "Container", "SDK", "API",
    "DGX", "OVX", "Slurm", "Bright Computing", "Base Command", "Base Command Manager",
    "Auto Scaler", "RTX", "HGX", "EGX", "AGX", "MLNX", "Magnum IO", "DOCA", "Forge",
    "DPU", "NIC", "Switch", "SOC", "SuperPOD"
]

def protect_text(text: str, protected_terms: List[str]) -> Tuple[str, Dict[str, str]]:
    """Replace protected terms and patterns with placeholders."""
    placeholders = {}
    protected_text = text
    
    # 1. Protect explicit terms (case-insensitive but preserve original for restoration)
    # Sort by length descending to avoid partial matches
    for i, term in enumerate(sorted(protected_terms, key=len, reverse=True)):
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        matches = pattern.findall(protected_text)
        for match in set(matches):
            placeholder = f"[[TERM_{len(placeholders)}]]"
            placeholders[placeholder] = match
            protected_text = protected_text.replace(match, placeholder)
            
    # 2. Protect ALL CAPS words (likely acronyms)
    acronyms = re.findall(r'\b[A-Z]{2,}\b', protected_text)
    for acronym in set(acronyms):
        if acronym not in placeholders.values():
            placeholder = f"[[TERM_{len(placeholders)}]]"
            placeholders[placeholder] = acronym
            protected_text = protected_text.replace(acronym, placeholder)
            
    return protected_text, placeholders

def restore_text(text: str, placeholders: Dict[str, str]) -> str:
    """Restore placeholders with original terms."""
    restored_text = text
    for placeholder, original in placeholders.items():
        restored_text = restored_text.replace(placeholder, original)
    return restored_text

def translate_text(text: str, target_lang: str, provider: str = "ollama", protected_terms: List[str] = None) -> str:
    """Translate a single string using the specified provider with fallback and term protection."""
    if not text.strip():
        return text

    if protected_terms is None:
        protected_terms = DEFAULT_PROTECTED_TERMS

    # Protect terms
    protected_text, placeholders = protect_text(text, protected_terms)

    translated_text = ""
    
    # Primary: Ollama (translategemma:4b)
    if provider == "ollama":
        try:
            import ollama
            response = ollama.chat(
                model='translategemma:4b',
                messages=[
                    {'role': 'user', 'content': f'Translate to {target_lang}: {protected_text}'}
                ]
            )
            translated_text = response['message']['content'].strip()
        except Exception as e:
            print(f"Ollama translation failed: {e}. Falling back to Google.")
            provider = "google"

    # Secondary: Google
    if provider == "google":
        try:
            from deep_translator import GoogleTranslator
            translated_text = GoogleTranslator(source='auto', target=target_lang).translate(protected_text)
        except Exception as e:
            print(f"Google translation failed: {e}")
            return text

    # Manual: OpenAI (if specifically requested)
    if provider == "openai":
        try:
            from openai import OpenAI
            client = OpenAI() # Assumes OPENAI_API_KEY is in environment
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are a professional translator. Translate the following text to {target_lang}. Preserve formatting like [[TERM_N]] placeholders. Output ONLY the translated text."},
                    {"role": "user", "content": protected_text}
                ]
            )
            translated_text = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI translation failed: {e}")
            return text

    if not translated_text:
        return text

    # Restore protected terms
    return restore_text(translated_text, placeholders)

def translate_inventory(inventory: Dict[str, Any], target_lang: str, provider: str = "ollama", skip_notes: bool = False, protected_terms: List[str] = None) -> Dict[str, Any]:
    """Iterate through the inventory and translate all text fields."""
    translated_inventory = {}
    
    total_slides = len(inventory)
    for i, (slide_key, slide_data) in enumerate(inventory.items()):
        print(f"Translating {slide_key} ({i+1}/{total_slides})...")
        translated_slide = {}
        
        for key, value in slide_data.items():
            if key == "notes":
                if skip_notes:
                    # Do not include notes in translated inventory so they remain original
                    continue
                # Translate notes string
                translated_slide[key] = translate_text(value, target_lang, provider, protected_terms)
            elif isinstance(value, dict) and "paragraphs" in value:
                # Translate paragraphs in a shape
                translated_shape = value.copy()
                translated_paragraphs = []
                for para in value["paragraphs"]:
                    translated_para = para.copy()
                    if "text" in para:
                        translated_para["text"] = translate_text(para["text"], target_lang, provider, protected_terms)
                    translated_paragraphs.append(translated_para)
                translated_shape["paragraphs"] = translated_paragraphs
                translated_slide[key] = translated_shape
            else:
                # Keep other fields as is
                translated_slide[key] = value
        
        translated_inventory[slide_key] = translated_slide
        
    return translated_inventory

def main():
    parser = argparse.ArgumentParser(description="Translate PowerPoint presentation.")
    parser.add_argument("input", help="Input PPTX file")
    parser.add_argument("output", help="Output PPTX file")
    parser.add_argument("lang", help="Target language code (e.g., 'zh-CN', 'en', 'ja')")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "google", "openai"], help="Translation provider (default: ollama)")
    parser.add_argument("--skip-notes", action="store_true", help="Skip translating speaker notes")
    parser.add_argument("--terms", help="Comma-separated list of terms to keep in English")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' not found")
        sys.exit(1)
        
    # Build protected terms list
    protected_terms = DEFAULT_PROTECTED_TERMS.copy()
    if args.terms:
        user_terms = [t.strip() for t in args.terms.split(",")]
        protected_terms.extend(user_terms)
        
    print(f"Extracting content from {args.input}...")
    inventory = get_inventory_as_dict(input_path)
    
    print(f"Translating content to {args.lang} using {args.provider}...")
    translated_inventory = translate_inventory(inventory, args.lang, args.provider, args.skip_notes, protected_terms)
    
    # Save temporary replacement JSON
    temp_json = Path("temp_replacement.json")
    with open(temp_json, "w", encoding="utf-8") as f:
        json.dump(translated_inventory, f, indent=2, ensure_ascii=False)
        
    # Apply translated content to output
    print(f"Applying translated content to {args.output}...")
    try:
        # Override environment to skip strict overflow validation during translation
        # since translated text (especially zh-CN) often has different measurement characteristics
        os.environ["SKIP_OVERFLOW_VALIDATION"] = "1"
        apply_replacements(str(input_path), str(temp_json), str(output_path))
        print("Translation completed successfully!")
    except Exception as e:
        print(f"Error applying replacements: {e}")
    finally:
        if temp_json.exists():
            temp_json.unlink()

if __name__ == "__main__":
    main()
