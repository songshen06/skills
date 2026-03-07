# Technical Presentation Guidelines

This guide defines strict constraints and best practices for creating "Technical Report Presentations". 
You must follow these rules when generating PPT content to ensure it is suitable for quick scanning and high-impact communication.

## Core Philosophy

**You are generating a [Technical Report Presentation], NOT a technical document, design spec, or README.**

### Audience Profile
- **Mixed technical backgrounds**: Not everyone is an expert in your specific domain.
- **Limited attention span**: Can only spend 5~10 seconds scanning each slide.
- **Goal**: They need to understand the *problem*, the *decision*, and the *control* over complexity.

### Your Goal
- **NOT**: "Explain every technical detail."
- **INSTEAD**: 
    - Make them quickly understand the problem being solved.
    - Make them remember key architectural decisions and trade-offs.
    - Make them believe system complexity is effectively controlled.

## Failure Criteria (Automatic Refactor Triggers)

If any of the following are true, the slide is considered a **FAILURE** and must be refactored:
- ❌ Looks like a Word doc, Wiki page, or dense spec.
- ❌ Contains more than 2 distinct technical sub-concepts per slide.
- ❌ Requires >10 seconds to read and grasp the core message.
- ❌ Information density is high; lacks white space (negative space).

## General Generation Rules (Strict Compliance)

1.  **One Key Message Per Slide**: Each slide must convey exactly **ONE** technical conclusion or judgment.
2.  **Judgment-Based Titles**: Titles must be **Judgments** or **Conclusions**.
    - ⛔ **Forbidden**: "Background", "Introduction", "Overview", "Architecture Description".
    - ✅ **Allowed**: "Microservices Reduce Deployment Risk", "Cache Layer Improves Latency by 50%".
3.  **Supportive Content Only**: Body text exists *only* to support the title's judgment. Do not explain for the sake of explaining.
4.  **Word Count Limit**: Total body text < **30 Chinese characters** (or ~20 English words).
5.  **Bullet Points**:
    - Max **3** items.
    - Max **12** words per item.

**Rule of Thumb**: Better to have incomplete information than visual/cognitive congestion.

## Slide Type Constraints (Only Use These 4 Types)

Before generating any slide, classify it into one of these 4 types:

### 1️⃣ Architecture Judgment Slide
- **Title**: A clear technical or architectural conclusion.
- **Body**: 1~2 pieces of evidence supporting the conclusion.

### 2️⃣ Architecture Comparison Slide
- **Left**: Rejected Option.
- **Right**: Chosen Option.
- **Center/Bottom**: 1 Key Trade-off Reason (Why we chose Right over Left).
- **Constraint**: **NO** third option allowed. Keep it binary for clarity.

### 3️⃣ System Structure Slide (De-engineered)
- **Content**: Only core modules that help the audience "remember the structure".
- **Constraint**: Omit secondary components. **NEVER** show full/comprehensive wiring.
- **Visual**: Focus on high-level data flow or logical grouping.

### 4️⃣ Transition Slide (Pacing Control)
- **Role**: Rhythm control; reducing cognitive load.
- **Content**: One sentence only.
- **Frequency**: Must insert 1 Transition Slide after every 3~4 technical slides.

## Visual & Aesthetic Constraints

- **White Space**: High priority. White space is active design, not empty space.
- **Scan-ability**: Prioritize "understood at a glance" over "complete accuracy".
- **Tone**:
    - Avoid explanatory paragraphs.
    - Avoid self-validating fluff ("We successfully implemented...").
    - Avoid "Ugly for the sake of Rigor".

**Final Check**: Assume this slide will be photographed by a phone from the back of the room and scanned in 5 seconds. Does it work?
