# -*- coding: utf-8 -*-
"""
Checker tools for the Multi-Agent RAG application.
These tools analyze and correct content issues.

File: custom_tools/checkers.py
"""

import re
import logging
import string
from typing import Dict, Any, Optional, List, Tuple

# Import decorator from langchain to make tools easily accessible
from langchain_core.tools import tool as lc_tool

# Set up logging
logger = logging.getLogger(__name__)

@lc_tool
def check_grammar(content: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Perform basic grammar and style checking on content.
    
    Args:
        content: The text content to check
        options: Optional checking preferences
            - strictness: "low", "medium", or "high" (default: "medium")
            - fix_issues: whether to automatically fix issues (default: True)
            - check_style: whether to check style issues (default: True)
    
    Returns:
        Dict containing checked content and analysis
    """
    options = options or {}
    strictness = options.get("strictness", "medium")
    fix_issues = options.get("fix_issues", True)
    check_style = options.get("check_style", True)
    
    try:
        # Initialize results
        issues = []
        fixed_content = content
        
        # Basic sentence boundary detection
        sentences = []
        current_sentence = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                if current_sentence:
                    sentences.append(''.join(current_sentence))
                    current_sentence = []
                continue
            
            # Skip code blocks and metadata
            if line.startswith('```') or line.startswith('#'):
                continue
            
            # Split by sentence boundaries
            chars = list(line)
            i = 0
            while i < len(chars):
                char = chars[i]
                current_sentence.append(char)
                
                # Check for sentence boundary
                if char in ['.', '!', '?'] and i + 1 < len(chars):
                    # Make sure it's not part of an abbreviation, number, etc.
                    if i + 1 < len(chars) and chars[i + 1] == ' ':
                        # It's likely a sentence boundary
                        if i + 2 < len(chars) and chars[i + 2].isupper():
                            sentences.append(''.join(current_sentence))
                            current_sentence = []
                i += 1
            
            # Add any remaining content as a sentence
            if current_sentence:
                sentences.append(''.join(current_sentence))
                current_sentence = []
        
        # Add any final sentence
        if current_sentence:
            sentences.append(''.join(current_sentence))
        
        # Common grammar and style issues to check
        
        # 1. Double spacing
        double_spaces = len(re.findall(r'  +', content))
        if double_spaces > 0:
            issues.append({
                "type": "style",
                "severity": "low",
                "message": f"Found {double_spaces} instances of double spacing",
                "fixable": True
            })
            if fix_issues:
                fixed_content = re.sub(r'  +', ' ', fixed_content)
        
        # 2. Repeated words
        repeated_words = re.findall(r'\b(\w+)\s+\1\b', content, re.IGNORECASE)
        if repeated_words:
            issues.append({
                "type": "grammar",
                "severity": "medium",
                "message": f"Found repeated words: {', '.join(repeated_words[:5])}",
                "fixable": True
            })
            if fix_issues:
                fixed_content = re.sub(r'\b(\w+)(\s+\1\b)', r'\1', fixed_content, flags=re.IGNORECASE)
        
        # 3. Run-on sentences (simple heuristic)
        long_sentences = [s for s in sentences if len(s.split()) > 30]
        if long_sentences:
            issues.append({
                "type": "style",
                "severity": "medium" if strictness == "medium" else "high",
                "message": f"Found {len(long_sentences)} potentially long or run-on sentences",
                "fixable": False
            })
        
        # 4. Passive voice (simple detection)
        passive_patterns = [
            r'\b(?:am|is|are|was|were|be|being|been)\s+(\w+ed)\b',
            r'\b(?:am|is|are|was|were|be|being|been)\s+(\w+en)\b'
        ]
        
        passive_count = 0
        for pattern in passive_patterns:
            passive_count += len(re.findall(pattern, content, re.IGNORECASE))
        
        if passive_count > 0 and check_style and strictness != "low":
            issues.append({
                "type": "style",
                "severity": "low",
                "message": f"Found approximately {passive_count} instances of passive voice",
                "fixable": False
            })
        
        # 5. Missing punctuation at end of sentences
        missing_punct = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and not sentence[-1] in ['.', '!', '?', ':', ';', '"', "'"]:
                missing_punct += 1
        
        if missing_punct > 0:
            issues.append({
                "type": "grammar",
                "severity": "medium",
                "message": f"Found {missing_punct} sentences possibly missing end punctuation",
                "fixable": False
            })
        
        # 6. Common spelling errors (very basic)
        common_misspellings = {
            "accomodate": "accommodate",
            "acheive": "achieve",
            "accross": "across",
            "aggresive": "aggressive",
            "apparant": "apparent",
            "appearence": "appearance",
            "arguement": "argument",
            "assasinate": "assassinate",
            "basicly": "basically",
            "begining": "beginning",
            "beleive": "believe",
            "buisness": "business",
            "calender": "calendar",
            "camoflage": "camouflage",
            "catagory": "category",
            "cemetary": "cemetery",
            "changable": "changeable",
            "cheif": "chief",
            "collegue": "colleague",
            "comming": "coming",
            "commited": "committed",
            "concieve": "conceive",
            "congratulations": "congratulations"
        }
        
        misspellings_found = []
        for word, correction in common_misspellings.items():
            if re.search(r'\b' + word + r'\b', content, re.IGNORECASE):
                misspellings_found.append(f"{word} → {correction}")
        
        if misspellings_found:
            issues.append({
                "type": "spelling",
                "severity": "medium",
                "message": f"Found possible misspellings: {', '.join(misspellings_found[:5])}",
                "fixable": True
            })
            
            if fix_issues:
                for word, correction in common_misspellings.items():
                    fixed_content = re.sub(r'\b' + word + r'\b', correction, fixed_content, flags=re.IGNORECASE)
        
        # 7. Capitalization errors (simple checks)
        sentences_start = [s.strip() for s in sentences if s.strip()]
        missing_caps = sum(1 for s in sentences_start if s and s[0].islower())
        
        if missing_caps > 0:
            issues.append({
                "type": "grammar",
                "severity": "medium",
                "message": f"Found {missing_caps} sentences that may not start with a capital letter",
                "fixable": True
            })
            
            if fix_issues:
                # Fix sentence beginnings (simplistic approach)
                for i, sentence in enumerate(sentences_start):
                    if sentence and sentence[0].islower():
                        capitalized = sentence[0].upper() + sentence[1:]
                        fixed_content = fixed_content.replace(sentence, capitalized, 1)
        
        # 8. Inconsistent spacing after punctuation
        inconsistent_spacing = len(re.findall(r'[.!?][a-zA-Z]', content))
        
        if inconsistent_spacing > 0:
            issues.append({
                "type": "style",
                "severity": "low",
                "message": f"Found {inconsistent_spacing} instances of missing space after punctuation",
                "fixable": True
            })
            
            if fix_issues:
                fixed_content = re.sub(r'([.!?])([a-zA-Z])', r'\1 \2', fixed_content)
        
        # 9. Contractions consistency (basic check)
        contractions = re.findall(r"\b(can't|won't|isn't|aren't|don't|doesn't|didn't|wouldn't|couldn't|shouldn't)\b", content)
        expanded = re.findall(r"\b(cannot|will not|is not|are not|do not|does not|did not|would not|could not|should not)\b", content)
        
        if contractions and expanded and check_style and strictness != "low":
            issues.append({
                "type": "style",
                "severity": "low",
                "message": "Mixed use of contractions and expanded forms (e.g., 'don't' vs 'do not')",
                "fixable": False
            })
        
        # Calculate readability (Flesch-Kincaid Grade Level - simplified)
        if sentences:
            word_count = sum(len(s.split()) for s in sentences)
            avg_sentence_length = word_count / len(sentences)
            
            syllable_count = 0
            for sentence in sentences:
                words = sentence.split()
                for word in words:
                    # Simplified syllable counting
                    word = word.lower().strip(string.punctuation)
                    if not word:
                        continue
                    
                    # Count vowel groups
                    count = len(re.findall(r'[aeiouy]+', word))
                    
                    # Adjust for common patterns
                    if word.endswith('e'):
                        count -= 1
                    if word.endswith('le') and len(word) > 2 and word[-3] not in 'aeiouy':
                        count += 1
                    if count == 0:
                        count = 1
                    
                    syllable_count += count
            
            avg_syllables_per_word = syllable_count / word_count if word_count else 0
            
            # Simplified Flesch-Kincaid
            grade_level = 0.39 * avg_sentence_length + 11.8 * avg_syllables_per_word - 15.59
            grade_level = max(0, min(18, grade_level))  # Clamp to 0-18
            
            readability_assessment = "unknown"
            if grade_level < 6:
                readability_assessment = "very easy"
            elif grade_level < 8:
                readability_assessment = "easy"
            elif grade_level < 10:
                readability_assessment = "fairly easy"
            elif grade_level < 12:
                readability_assessment = "standard"
            elif grade_level < 14:
                readability_assessment = "fairly difficult"
            elif grade_level < 16:
                readability_assessment = "difficult"
            else:
                readability_assessment = "very difficult"
        else:
            grade_level = 0
            readability_assessment = "unknown"
            word_count = 0
            avg_sentence_length = 0
        
        # Final assessment
        return {
            "corrected_content": fixed_content,
            "issues_found": len(issues),
            "issues": issues,
            "readability": {
                "assessment": readability_assessment,
                "grade_level": round(grade_level, 1),
                "word_count": word_count,
                "sentence_count": len(sentences),
                "avg_sentence_length": round(avg_sentence_length, 1)
            },
            "fixes_applied": fix_issues
        }
    
    except Exception as e:
        logger.error(f"Error in grammar checker: {e}")
        return {
            "corrected_content": content,
            "issues_found": 0,
            "error": str(e),
            "fixes_applied": False
        }

@lc_tool
def check_facts(content: str, reference: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Perform fact checking against reference material.
    
    Args:
        content: The text content to check facts in
        reference: Optional reference text to check against
        options: Optional checking preferences
            - strictness: "low", "medium", or "high" (default: "medium")
            - highlight_discrepancies: whether to highlight issues (default: True)
    
    Returns:
        Dict containing fact checking results
    """
    options = options or {}
    strictness = options.get("strictness", "medium")
    highlight_discrepancies = options.get("highlight_discrepancies", True)
    
    try:
        # Initialize results
        discrepancies = []
        confidence_score = 0.0
        
        # If no reference text is provided, we can't do proper fact checking
        if not reference:
            return {
                "verified_content": content,
                "discrepancies_found": 0,
                "discrepancies": [],
                "confidence_score": 0.0,
                "message": "Cannot perform fact checking without reference material"
            }
        
        # Extract sentences from content
        content_sentences = []
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Split into sentences (simplistic)
            parts = re.split(r'(?<=[.!?])\s+', line)
            content_sentences.extend(parts)
        
        # Extract sentences from reference
        reference_sentences = []
        for line in reference.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Split into sentences (simplistic)
            parts = re.split(r'(?<=[.!?])\s+', line)
            reference_sentences.extend(parts)
        
        # Extract claimed facts from content
        facts = []
        for sentence in content_sentences:
            # Skip questions, commands, etc.
            if sentence.endswith('?') or sentence.endswith('!'):
                continue
            
            # Skip opinions and subjective statements
            opinion_markers = ['believe', 'think', 'feel', 'suggest', 'recommend', 'opinion', 
                            'maybe', 'perhaps', 'possibly', 'likely', 'might', 'could', 
                            'should', 'would', 'best', 'worst', 'good', 'bad']
            
            is_opinion = any(marker in sentence.lower() for marker in opinion_markers)
            if is_opinion:
                continue
            
            # Skip sentences that don't make claims
            if not any(word in sentence.lower() for word in ['is', 'are', 'was', 'were', 'has', 'have', 'had']):
                continue
            
            facts.append(sentence)
        
        # Check each fact against the reference
        total_confidence = 0
        checked_facts = 0
        
        for fact in facts:
            # Tokenize the fact
            fact_tokens = re.findall(r'\b\w+\b', fact.lower())
            
            # Skip very short facts
            if len(fact_tokens) < 3:
                continue
            
            # Look for supporting evidence in reference
            max_overlap = 0
            best_match = None
            
            for ref_sentence in reference_sentences:
                ref_tokens = re.findall(r'\b\w+\b', ref_sentence.lower())
                
                # Calculate token overlap
                common_tokens = set(fact_tokens) & set(ref_tokens)
                overlap_ratio = len(common_tokens) / len(fact_tokens) if fact_tokens else 0
                
                if overlap_ratio > max_overlap:
                    max_overlap = overlap_ratio
                    best_match = ref_sentence
            
            # Assess fact confidence
            fact_confidence = 0
            if max_overlap >= 0.8:
                fact_confidence = 1.0  # High confidence
            elif max_overlap >= 0.5:
                fact_confidence = 0.7  # Medium confidence
            elif max_overlap >= 0.3:
                fact_confidence = 0.3  # Low confidence
            else:
                fact_confidence = 0.0  # No confidence
            
            # Add to total confidence
            total_confidence += fact_confidence
            checked_facts += 1
            
            # Record discrepancies for low-confidence facts
            if fact_confidence < 0.5:
                discrepancies.append({
                    "claim": fact,
                    "confidence": fact_confidence,
                    "best_reference": best_match,
                    "overlap": max_overlap
                })
        
        # Calculate overall confidence score
        confidence_score = total_confidence / checked_facts if checked_facts > 0 else 0
        
        # Highlight discrepancies in content if requested
        verified_content = content
        if highlight_discrepancies and discrepancies:
            for discrepancy in discrepancies:
                claim = discrepancy["claim"]
                confidence = discrepancy["confidence"]
                
                # Add highlighting based on confidence
                if confidence == 0:
                    # Mark as highly questionable
                    replacement = f"[UNVERIFIED: {claim}]"
                elif confidence < 0.3:
                    # Mark as questionable
                    replacement = f"[QUESTIONABLE: {claim}]"
                else:
                    # Mark as low confidence
                    replacement = f"[LOW CONFIDENCE: {claim}]"
                
                verified_content = verified_content.replace(claim, replacement)
        
        return {
            "verified_content": verified_content,
            "discrepancies_found": len(discrepancies),
            "discrepancies": discrepancies[:5],  # Limit to 5 discrepancies for brevity
            "confidence_score": round(confidence_score, 2),
            "facts_checked": checked_facts
        }
    
    except Exception as e:
        logger.error(f"Error in fact checker: {e}")
        return {
            "verified_content": content,
            "discrepancies_found": 0,
            "confidence_score": 0.0,
            "error": str(e)
        }

@lc_tool
def check_coherence(content: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Check document coherence, focusing on logical flow and structure.
    
    Args:
        content: The text content to check
        options: Optional checking preferences
            - strictness: "low", "medium", or "high" (default: "medium")
            - highlight_issues: whether to highlight issues (default: True)
    
    Returns:
        Dict containing coherence analysis
    """
    options = options or {}
    strictness = options.get("strictness", "medium")
    highlight_issues = options.get("highlight_issues", True)
    
    try:
        # Initialize results
        issues = []
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        
        # Skip analysis if too little content
        if len(paragraphs) < 2:
            return {
                "analyzed_content": content,
                "coherence_score": 1.0,
                "issues_found": 0,
                "issues": [],
                "structure": {
                    "paragraphs": len(paragraphs),
                    "has_introduction": None,
                    "has_conclusion": None
                }
            }
        
        # Extract structure elements
        has_introduction = False
        has_conclusion = False
        topic_sentences = []
        
        # Check for introduction paragraph
        intro_markers = ['introduction', 'overview', 'background', 'context', 'first', 'begin', 'start']
        if any(marker in paragraphs[0].lower() for marker in intro_markers):
            has_introduction = True
        
        # Check for conclusion paragraph
        conclusion_markers = ['conclusion', 'summary', 'finally', 'in summary', 'to summarize', 
                             'in conclusion', 'to conclude', 'overall', 'thus', 'therefore']
        if any(marker in paragraphs[-1].lower() for marker in conclusion_markers):
            has_conclusion = True
        
        # Extract topic sentences
        for paragraph in paragraphs:
            sentences = re.split(r'(?<=[.!?])\s+', paragraph.strip())
            if sentences:
                topic_sentences.append(sentences[0])
        
        # Analyze cohesion
        transition_words = [
            'additionally', 'furthermore', 'moreover', 'similarly', 'likewise',
            'in contrast', 'conversely', 'however', 'nevertheless', 'nonetheless',
            'therefore', 'consequently', 'thus', 'hence', 'accordingly',
            'specifically', 'for example', 'for instance', 'to illustrate',
            'in conclusion', 'finally', 'in summary', 'to summarize'
        ]
        
        transition_count = 0
        for paragraph in paragraphs[1:]:  # Skip first paragraph
            if any(paragraph.lower().startswith(word) for word in transition_words):
                transition_count += 1
        
        transition_ratio = transition_count / (len(paragraphs) - 1) if len(paragraphs) > 1 else 0
        
        # Check topic continuity
        topic_continuity_issues = 0
        for i in range(1, len(topic_sentences)):
            prev_sentence = topic_sentences[i-1].lower()
            curr_sentence = topic_sentences[i].lower()
            
            # Check for topic overlap
            prev_words = set(re.findall(r'\b\w+\b', prev_sentence))
            curr_words = set(re.findall(r'\b\w+\b', curr_sentence))
            
            # Remove stopwords
            stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'so', 'as', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'like', 'from', 'is', 'are', 'was', 'were', 'be', 'been'}
            prev_words = prev_words - stopwords
            curr_words = curr_words - stopwords
            
            # Calculate overlap
            overlap = len(prev_words & curr_words)
            if overlap == 0:
                topic_continuity_issues += 1
        
        # Record issues
        if transition_ratio < 0.3 and strictness != "low":
            issues.append({
                "type": "cohesion",
                "severity": "medium",
                "message": f"Low use of transition words between paragraphs ({int(transition_ratio * 100)}%)"
            })
        
        if topic_continuity_issues > 0 and len(paragraphs) > 2:
            issues.append({
                "type": "coherence",
                "severity": "high" if topic_continuity_issues >= len(paragraphs) / 2 else "medium",
                "message": f"Found {topic_continuity_issues} paragraph transitions with potential topic discontinuity"
            })
        
        if not has_introduction and len(paragraphs) >= 3:
            issues.append({
                "type": "structure",
                "severity": "medium",
                "message": "Document may be missing a clear introduction"
            })
        
        if not has_conclusion and len(paragraphs) >= 3:
            issues.append({
                "type": "structure",
                "severity": "medium",
                "message": "Document may be missing a clear conclusion"
            })
        
        # Calculate overall coherence score (0-1)
        topic_continuity_score = 1 - (topic_continuity_issues / (len(paragraphs) - 1) if len(paragraphs) > 1 else 0)
        transition_score = min(1, transition_ratio * 2)  # Scale transition ratio
        structure_score = (0.5 + 0.25 * has_introduction + 0.25 * has_conclusion)
        
        coherence_score = (topic_continuity_score * 0.4 + transition_score * 0.3 + structure_score * 0.3)
        
        # Highlight issues in content if requested
        analyzed_content = content
        if highlight_issues and issues:
            # Add comments at the top
            comments = ["# Coherence Analysis"]
            for issue in issues:
                comments.append(f"# {issue['severity'].upper()}: {issue['message']}")
            
            analyzed_content = '\n'.join(comments) + '\n\n' + content
        
        return {
            "analyzed_content": analyzed_content,
            "coherence_score": round(coherence_score, 2),
            "issues_found": len(issues),
            "issues": issues,
            "structure": {
                "paragraphs": len(paragraphs),
                "has_introduction": has_introduction,
                "has_conclusion": has_conclusion,
                "transition_ratio": round(transition_ratio, 2)
            }
        }
    
    except Exception as e:
        logger.error(f"Error in coherence checker: {e}")
        return {
            "analyzed_content": content,
            "coherence_score": 0.0,
            "issues_found": 0,
            "error": str(e)
        }

@lc_tool
def check_readability(content: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze text readability using standard metrics.
    
    Args:
        content: The text content to analyze
        options: Optional analysis preferences
            - metrics: List of metrics to calculate (default: ["flesch_kincaid", "smog", "coleman_liau"])
            - target_audience: Target audience level (default: "general")
    
    Returns:
        Dict containing readability analysis
    """
    options = options or {}
    metrics = options.get("metrics", ["flesch_kincaid", "smog", "coleman_liau"])
    target_audience = options.get("target_audience", "general")
    
    try:
        # Initialize results
        results = {}
        audience_match = True
        audience_suggestions = []
        
        # Extract paragraphs, sentences, and words
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        
        # Extract sentences
        sentences = []
        for paragraph in paragraphs:
            # Split by sentence boundaries (simplistic)
            parts = re.split(r'(?<=[.!?])\s+', paragraph.strip())
            sentences.extend([p for p in parts if p.strip()])
        
        # Skip analysis if too little content
        if len(sentences) < 3:
            return {
                "readability_scores": {},
                "audience_match": None,
                "word_count": 0,
                "sentence_count": len(sentences),
                "average_sentence_length": 0,
                "suggestions": ["Text is too short for meaningful readability analysis"]
            }
        
        # Count words and syllables
        words = []
        syllable_count = 0
        complex_word_count = 0  # Words with 3+ syllables
        
        for sentence in sentences:
            sentence_words = re.findall(r'\b[a-zA-Z]+\b', sentence)
            words.extend(sentence_words)
            
            for word in sentence_words:
                # Simplified syllable counting
                word = word.lower()
                
                # Count vowel groups
                count = len(re.findall(r'[aeiouy]+', word))
                
                # Adjust for common patterns
                if word.endswith('e'):
                    count -= 1
                if word.endswith('le') and len(word) > 2 and word[-3] not in 'aeiouy':
                    count += 1
                if count == 0:
                    count = 1
                
                syllable_count += count
                
                # Count complex words
                if count >= 3:
                    complex_word_count += 1
        
        word_count = len(words)
        average_sentence_length = word_count / len(sentences) if sentences else 0
        average_syllables_per_word = syllable_count / word_count if word_count else 0
        
        # Calculate Flesch-Kincaid Grade Level
        if "flesch_kincaid" in metrics:
            fk_grade = 0.39 * average_sentence_length + 11.8 * average_syllables_per_word - 15.59
            fk_grade = max(0, min(18, fk_grade))  # Clamp to 0-18
            results["flesch_kincaid_grade"] = round(fk_grade, 1)
        
        # Calculate Flesch Reading Ease
        if "flesch_reading_ease" in metrics:
            reading_ease = 206.835 - 1.015 * average_sentence_length - 84.6 * average_syllables_per_word
            reading_ease = max(0, min(100, reading_ease))  # Clamp to 0-100
            results["flesch_reading_ease"] = round(reading_ease, 1)
        
        # Calculate SMOG Index
        if "smog" in metrics and len(sentences) >= 30:
            # Need 30 sentences for accurate SMOG
            smog_index = 1.043 * ((complex_word_count * (30 / len(sentences))) ** 0.5) + 3.1291
            results["smog_index"] = round(smog_index, 1)
        
        # Calculate Coleman-Liau Index
        if "coleman_liau" in metrics:
            # Count letters
            letter_count = sum(len(word) for word in words)
            L = (letter_count / word_count) * 100 if word_count else 0
            S = (len(sentences) / word_count) * 100 if word_count else 0
            
            cli = 0.0588 * L - 0.296 * S - 15.8
            results["coleman_liau_index"] = round(cli, 1)
        
        # Automated Readability Index
        if "ari" in metrics:
            # Count characters (including spaces)
            char_count = len(content)
            
            ari = 4.71 * (char_count / word_count) + 0.5 * (word_count / len(sentences)) - 21.43
            ari = max(1, min(14, ari))  # Clamp to 1-14
            results["automated_readability_index"] = round(ari, 1)
        
        # Determine audience match based on Flesch-Kincaid Grade Level
        if "flesch_kincaid_grade" in results:
            grade = results["flesch_kincaid_grade"]
            
            audience_levels = {
                "elementary": (1, 5),
                "middle_school": (6, 8),
                "high_school": (9, 12),
                "college": (13, 16),
                "graduate": (17, 18),
                "general": (7, 10)
            }
            
            target_range = audience_levels.get(target_audience, audience_levels["general"])
            
            if grade < target_range[0]:
                audience_match = False
                audience_suggestions.append(f"Text may be too simple for {target_audience} audience (grade level: {grade}).")
                audience_suggestions.append("Consider using more precise terminology and slightly longer sentences.")
            elif grade > target_range[1]:
                audience_match = False
                audience_suggestions.append(f"Text may be too complex for {target_audience} audience (grade level: {grade}).")
                audience_suggestions.append("Consider using shorter sentences and simpler vocabulary.")
            else:
                audience_match = True
                audience_suggestions.append(f"Text complexity appears appropriate for {target_audience} audience.")
        
        # Additional information
        reading_speed_wpm = 250  # Average adult reading speed
        estimated_reading_time = word_count / reading_speed_wpm
        
        # Convert to minutes and seconds
        reading_minutes = int(estimated_reading_time)
        reading_seconds = int((estimated_reading_time - reading_minutes) * 60)
        
        return {
            "readability_scores": results,
            "audience_match": audience_match,
            "word_count": word_count,
            "sentence_count": len(sentences),
            "average_sentence_length": round(average_sentence_length, 1),
            "complex_word_percentage": round((complex_word_count / word_count) * 100, 1) if word_count else 0,
            "estimated_reading_time": f"{reading_minutes}m {reading_seconds}s",
            "suggestions": audience_suggestions
        }
    
    except Exception as e:
        logger.error(f"Error in readability checker: {e}")
        return {
            "readability_scores": {},
            "audience_match": None,
            "word_count": 0,
            "error": str(e)
        }