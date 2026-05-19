# AI Workflow for Construction Quality & Compliance Platform

## Purpose

This document explains how the AI part of the platform should work for image and video inspection, Saudi code compliance checking, RAG-based code retrieval, bounding box annotation, and report generation.

The important idea is:

> The LLM should not receive the full Saudi code document every time. The code document should be stored in a vector database, and only the relevant clauses should be retrieved for each AI finding.

## High-Level AI Flow

```text
Supervisor captures image/video
        |
        v
Backend stores original media
        |
        v
GLM-4.6V analyzes image/video
        |
        v
Structured visual findings are generated
        |
        v
Each finding is used as a RAG search query
        |
        v
Relevant Saudi code clauses are retrieved from vector DB
        |
        v
LLM verifies compliance against retrieved clauses
        |
        v
OpenCV renders bounding boxes and labels
        |
        v
Compliance report is generated
```

## Full System Flow

```text
Mobile App
  |
  | 1. Capture image/video using in-app camera
  v
Backend API
  |
  | 2. Validate task, user, geofence, file type, file size
  v
Object Storage
  |
  | 3. Store original image/video
  v
AI Processing Queue
  |
  | 4. Start async AI job
  v
GLM-4.6V
  |
  | 5. Analyze visual content
  |    - detect construction issues
  |    - identify timestamps for video
  |    - suggest bounding boxes
  |    - create search queries for RAG
  v
Structured Findings JSON
  |
  | 6. For each finding, search Saudi code vector DB
  v
Vector DB
  |
  | 7. Return top matching Saudi code clauses
  v
Compliance Verifier LLM
  |
  | 8. Compare visual finding with retrieved code clauses
  |    - compliant / non-compliant
  |    - matched clause
  |    - risk level
  |    - reason
  |    - remediation
  v
OpenCV Annotation Service
  |
  | 9. Draw bounding boxes, labels, risk colors
  v
Report Generator
  |
  | 10. Generate PDF report with evidence and code references
  v
Web Portal / Mobile App
```

## Main Components

### 1. GLM-4.6V

GLM-4.6V is responsible for visual understanding.

It should analyze:

- inspection images
- inspection videos
- construction defects
- visible safety/compliance problems
- video timestamps
- rough violation regions

Expected output:

```json
{
  "overall_status": "non_compliant",
  "findings": [
    {
      "finding_id": "F-001",
      "media_type": "video",
      "timestamp": "00:01:24",
      "category": "Electrical Installation",
      "observation": "Exposed electrical wiring is visible near an active work area.",
      "possible_violation": "Exposed wiring without protection",
      "risk_hint": "High",
      "bbox": {
        "x": 320,
        "y": 180,
        "width": 240,
        "height": 160
      },
      "rag_query": "Saudi building code exposed electrical wiring protection construction site"
    }
  ]
}
```

GLM-4.6V should not be trusted alone for final code compliance. It should first produce observations, then the RAG system should retrieve the relevant Saudi code clauses.

### 2. Saudi Code RAG System

The Saudi code document may be very long, so it should not be passed fully to the LLM.

Instead:

```text
Saudi code document
  -> extract text
  -> clean text
  -> split by chapter/section/clause
  -> create embeddings
  -> store in vector DB
```

Each clause should be stored with metadata:

```json
{
  "clause_id": "SBC-E-4.2.1",
  "source": "Saudi Building Code - Electrical",
  "category": "Electrical Installation",
  "chapter": "Wiring Protection",
  "section": "Protection from Physical Damage",
  "text": "Electrical conductors shall be protected from physical damage using approved raceways, conduits, or equivalent protection.",
  "page": 42
}
```

When GLM-4.6V finds an issue, the backend searches the vector DB using:

- finding category
- visual observation
- possible violation
- generated `rag_query`

Example:

```text
Query:
Electrical Installation exposed wiring without protection active construction site

Retrieved clauses:
1. SBC-E-4.2.1 - Protection from physical damage
2. SBC-E-4.3.5 - Approved raceways and conduits
3. SBC-SAFE-2.1 - Temporary site electrical safety
```

### 3. Compliance Verifier LLM

This step makes the final decision using only the retrieved clauses.

Input:

```text
Visual finding:
- Category: Electrical Installation
- Observation: Exposed electrical wiring is visible near an active work area.
- Timestamp: 00:01:24
- Risk hint: High

Retrieved Saudi code clauses:
1. SBC-E-4.2.1: Electrical conductors shall be protected from physical damage...
2. SBC-E-4.3.5: Wiring shall be installed in approved raceways...

Task:
Decide if the finding is compliant or non-compliant.
Return matched clause, reason, risk level, remediation, and confidence.
```

Output:

```json
{
  "finding_id": "F-001",
  "compliance_status": "non_compliant",
  "matched_clause_id": "SBC-E-4.2.1",
  "risk_level": "High",
  "reason": "The wiring appears exposed and is not protected from physical damage.",
  "remediation": "Install approved conduit/raceway or other protection before continuing work.",
  "confidence": 0.82
}
```

### 4. OpenCV

OpenCV is not the main compliance brain. It is mainly for visual processing and rendering.

Use OpenCV for:

- drawing bounding boxes
- drawing labels
- drawing risk color overlays
- cropping violation zones
- generating key frame images
- creating annotated evidence for PDF reports

Risk colors:

```text
Critical = Red
High     = Orange
Medium   = Yellow
Low      = Blue
```

### 5. FFmpeg

If GLM-4.6V accepts full video input directly, FFmpeg is not mandatory for AI analysis.

Still, FFmpeg is useful for:

- video thumbnail generation
- extracting key frames for reports
- compressing large videos
- reading video metadata
- fallback frame extraction if direct video analysis fails
- cutting short clips around violation timestamps

Recommended approach:

```text
Primary path:
GLM-4.6V analyzes full video directly

Fallback/support path:
FFmpeg extracts frames or clips when needed
```

## Image Analysis Flow

```text
Image captured
  |
  v
Store original image
  |
  v
Send image to GLM-4.6V
  |
  v
Get visual findings and bounding boxes
  |
  v
Search Saudi code vector DB for each finding
  |
  v
Verify compliance using retrieved clauses
  |
  v
Render annotated image with OpenCV
  |
  v
Generate final inspection report
```

## Video Analysis Flow

```text
Video captured
  |
  v
Store original video
  |
  v
Send full video to GLM-4.6V
  |
  v
Get timestamped findings
  |
  v
For each finding:
    - retrieve Saudi code clauses using RAG
    - verify compliance
    - extract key frame or clip if needed
    - draw bounding box/label with OpenCV
  |
  v
Build violation timeline
  |
  v
Generate report with timestamps, key frames, clauses, and remediation
```

## Data Stored in Each System

### Object Storage

Store large media files:

- original images
- original videos
- annotated images
- annotated key frames
- generated PDF reports

### Database

Store application records:

- inspections
- tasks
- projects
- users
- companies
- AI job status
- findings
- matched clauses
- report metadata

### Vector Database

Store Saudi code knowledge:

- Saudi code clauses
- clause embeddings
- source document name
- page number
- chapter
- section
- category

Do not store videos in the vector DB.

## Recommended AI Job Statuses

```text
uploaded
queued
analyzing_media
retrieving_code_clauses
verifying_compliance
annotating_media
generating_report
completed
failed
```

## Recommended Tech Stack

| Area | Suggested Tool |
| --- | --- |
| Video/image understanding | GLM-4.6V |
| RAG embeddings | OpenAI embeddings, BGE, or similar embedding model |
| Vector DB | PostgreSQL + pgvector, Qdrant, Pinecone, or Chroma |
| Bounding boxes/annotation | OpenCV |
| Video support/fallback | FFmpeg |
| Async processing | Celery, RQ, BullMQ, or cloud queue |
| Media storage | S3-compatible object storage |
| Report generation | HTML to PDF, WeasyPrint, Playwright PDF, or wkhtmltopdf |

## Estimated Build Time for AI Part

The estimate depends on whether this is a prototype or production-ready system.

### Prototype AI Pipeline

Estimated time: **10 to 15 working days**

Scope:

- upload image/video
- send media to GLM-4.6V
- get structured findings
- ingest Saudi code document into vector DB
- retrieve relevant clauses
- generate compliance result
- draw basic bounding boxes
- generate simple report

### MVP AI Pipeline

Estimated time: **20 to 30 working days**

Scope:

- robust media upload and storage
- async AI job processing
- full RAG ingestion pipeline
- clause-level metadata
- image/video analysis
- confidence scoring
- OpenCV annotation
- violation timeline for videos
- PDF report generation
- error handling and retries
- admin review workflow

### Production-Ready AI Pipeline

Estimated time: **45 to 75 working days**

Scope:

- all MVP features
- scalable queue workers
- model prompt tuning
- Saudi code document versioning
- evaluation dataset
- human review and correction loop
- audit trail
- tenant isolation
- monitoring
- cost control
- fallback processing
- security hardening
- accuracy testing with real site images/videos

## Practical Recommendation

Start with the MVP in this order:

1. Build Saudi code ingestion into vector DB.
2. Build image analysis with GLM-4.6V.
3. Connect image findings to RAG retrieval.
4. Add compliance verifier prompt.
5. Add OpenCV annotation for images.
6. Add video analysis using direct GLM-4.6V video input.
7. Add FFmpeg only for thumbnails, key frames, and fallback.
8. Generate PDF reports.
9. Add review workflow and confidence scoring.

Best starting target:

```text
First milestone: image compliance analysis + RAG + annotated report
Estimated time: 7 to 10 working days

Second milestone: video compliance analysis + timestamped findings
Estimated time: 10 to 15 working days
```

