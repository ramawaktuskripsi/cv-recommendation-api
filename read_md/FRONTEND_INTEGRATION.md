# 🔗 Frontend Integration - Quick Reference

Panduan singkat untuk rekan frontend mengintegrasikan CV Parser API.

---

## 📋 Schema Prisma yang Relevan

```prisma
model applications {
  id              String            @id
  jobId           String
  jobseekerId     String
  resumeUrl       String?           // CV URL
  status          ApplicationStatus
  recruiterNotes  String?           // Simpan AI result di sini (JSON)
  reviewedAt      DateTime?
  rejectionReason String?
  jobs            jobs              @relation(...)
  jobseekers      jobseekers        @relation(...)
}

model jobs {
  id         String       @id
  title      String
  job_skills job_skills[] // Required skills
}

model job_skills {
  id         String  @id
  jobId      String
  skillId    String
  isRequired Boolean @default(true)
  skills     skills  @relation(...)
}

model skills {
  id   String @id
  name String @unique  // "Quality Control", "Leadership", etc.
}
```

---

## 🚀 API Integration

### **Endpoint:**
```
POST https://your-cv-parser-api.railway.app/api/process-complete
```

### **Request:**
```typescript
const response = await fetch(API_URL + '/api/process-complete', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    cv_url: application.resumeUrl,        // dari Supabase
    job_id: application.jobId,
    application_id: application.id,
    job_title: job.title,
    required_skills: ["Quality Control", "Leadership", "SAP"]  // dari job_skills
  })
})
```

### **Response (RECOMMENDED):**
```json
{
  "success": true,
  "data": {
    "application_id": "app-123",
    "candidate": {
      "name": "John Doe",
      "email": "john@example.com",
      "skills": ["Quality Control", "Leadership"]
    },
    "matching": {
      "statistics": {
        "matched_count": 2,
        "total_required": 3,
        "match_percentage": 67.0
      }
    },
    "recommendation": {
      "status": "RECOMMENDED",
      "score": 67.0
    }
  }
}
```

### **Response (NOT RECOMMENDED):**
```json
{
  "success": false,
  "reason": "NOT_RECOMMENDED",
  "message": "No matching skills found",
  "application_id": "app-123"
}
```

---

## 💻 Implementation Example

```typescript
// /api/applications/[id]/process-cv/route.ts

import { prisma } from '@/lib/prisma'

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  const applicationId = params.id
  
  // 1. Get application with job skills
  const application = await prisma.applications.findUnique({
    where: { id: applicationId },
    include: {
      jobs: {
        include: {
          job_skills: {
            where: { isRequired: true },
            include: { skills: true }
          }
        }
      },
      jobseekers: {
        select: { resumeUrl: true, cvUrl: true }
      }
    }
  })
  
  if (!application) {
    return Response.json({ error: 'Not found' }, { status: 404 })
  }
  
  // 2. Get CV URL
  const cvUrl = application.resumeUrl || 
                application.jobseekers.cvUrl ||
                application.jobseekers.resumeUrl
  
  if (!cvUrl) {
    return Response.json({ error: 'No CV found' }, { status: 400 })
  }
  
  // 3. Extract required skills
  const requiredSkills = application.jobs.job_skills.map(js => js.skills.name)
  
  // 4. Call CV Parser API
  const result = await fetch(process.env.CV_PARSER_API_URL + '/api/process-complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cv_url: cvUrl,
      job_id: application.jobId,
      application_id: application.id,
      job_title: application.jobs.title,
      required_skills: requiredSkills
    })
  }).then(res => res.json())
  
  // 5. Update application
  if (result.success) {
    // RECOMMENDED
    await prisma.applications.update({
      where: { id: applicationId },
      data: {
        status: 'SHORTLISTED',
        recruiterNotes: JSON.stringify({
          aiParsing: {
            matchScore: result.data.recommendation.score,
            matchedSkills: result.data.matching.statistics.matched_count,
            totalRequired: result.data.matching.statistics.total_required,
            candidateSkills: result.data.candidate.skills,
            parsedAt: new Date()
          }
        }),
        reviewedAt: new Date()
      }
    })
  } else {
    // NOT RECOMMENDED
    await prisma.applications.update({
      where: { id: applicationId },
      data: {
        status: 'REJECTED',
        rejectionReason: 'No matching skills found',
        reviewedAt: new Date()
      }
    })
  }
  
  return Response.json(result)
}
```

---

## 🎯 Frontend Component

```typescript
'use client'

import { useState } from 'react'

export function ProcessCVButton({ applicationId }: { applicationId: string }) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  
  const handleProcess = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/applications/${applicationId}/process-cv`, {
        method: 'POST'
      })
      const data = await res.json()
      setResult(data)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div>
      <button onClick={handleProcess} disabled={loading}>
        {loading ? 'Processing...' : 'AI Screen CV'}
      </button>
      
      {result?.success && (
        <div className="mt-4 p-4 bg-green-50 rounded">
          <h3 className="font-bold">✅ RECOMMENDED</h3>
          <p>Match Score: {result.data.recommendation.score}%</p>
          <p>Matched: {result.data.matching.statistics.matched_count}/{result.data.matching.statistics.total_required} skills</p>
          <p>Candidate: {result.data.candidate.name}</p>
        </div>
      )}
      
      {result?.success === false && (
        <div className="mt-4 p-4 bg-red-50 rounded">
          <h3 className="font-bold">❌ NOT RECOMMENDED</h3>
          <p>{result.message}</p>
        </div>
      )}
    </div>
  )
}
```

---

## 🔧 Environment Variables

```env
# .env.local
CV_PARSER_API_URL=https://your-cv-parser-api.railway.app
```

---

## ✅ Checklist

- [ ] Setup environment variable `CV_PARSER_API_URL`
- [ ] Create API route `/api/applications/[id]/process-cv`
- [ ] Implement CV processing logic
- [ ] Add UI button untuk trigger processing
- [ ] Handle RECOMMENDED response
- [ ] Handle NOT RECOMMENDED response
- [ ] Test dengan sample CV

---

## 📞 Support

Jika ada issues:
1. Check API health: `GET /api/health`
2. Check logs di Railway dashboard
3. Verify CV URL is accessible (PDF only)
4. Verify required_skills array is not empty
