import { NextResponse } from 'next/server'
import { GoogleGenerativeAI } from '@google/generative-ai'

export async function POST(request) {
  try {
    const { setId, indicationDescription } = await request.json()
    if (!setId) {
      return NextResponse.json({ error: 'setId is required' }, { status: 400 })
    }

    // Step 1: Fetch DailyMed HTML page
    const dailymedUrl = `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=${setId}`
    const htmlResponse = await fetch(dailymedUrl)
    if (!htmlResponse.ok) {
      return NextResponse.json({ error: 'Failed to fetch DailyMed page' }, { status: 502 })
    }
    const html = await htmlResponse.text()

    // Step 2: Extract Section 14 (Clinical Studies)
    const section14Text = extractSection14(html)
    if (!section14Text || section14Text.length < 50) {
      return NextResponse.json({ error: 'Could not extract Section 14 from DailyMed', section14Text: section14Text || '' }, { status: 404 })
    }

    // Step 3: For very large sections (like OPDIVO with 28 NCTs),
    // truncate to keep within Gemini's practical limits but keep all NCT references
    const textForGemini = section14Text.length > 30000 ? truncateKeepingNcts(section14Text, 30000) : section14Text

    // Step 4: Send to Gemini to extract all NCT IDs
    const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY)
    const model = genAI.getGenerativeModel({
      model: 'gemini-2.0-flash',
      generationConfig: { temperature: 0 }
    })

    const prompt = indicationDescription
      ? `You are a clinical research expert performing a strict matching task.

INDICATION TO MATCH:
"${indicationDescription}"

TASK: In the Section 14 text below, find the subsection that DIRECTLY describes the clinical trial(s) for the EXACT indication above. Return ONLY the NCT ID(s) that appear within that specific subsection.

STRICT RULES:
- Section 14 is organized by subsections (14.1, 14.2, 14.3, etc.), each covering a different cancer type or setting.
- Find the subsection that matches the cancer type, stage, combination, and line of therapy in the indication.
- Return ONLY NCT IDs explicitly written in that matching subsection.
- Do NOT include NCTs from other subsections, even if they involve the same drug.
- Do NOT infer or guess — only return NCTs that are literally printed in the matching subsection text.
- If the indication mentions "in combination with" a specific drug, only match subsections that study that exact combination.

Return ONLY valid JSON:
{
  "ncts": [
    { "nctId": "NCT12345678", "trialName": "TRIAL_NAME or empty string", "indication": "subsection cancer type" }
  ]
}

If no matching subsection is found, return: { "ncts": [] }

Section 14 text:
${textForGemini}`
      : `You are a clinical research expert. From the following Section 14 (Clinical Studies) text, extract ALL NCT IDs mentioned.

For each NCT ID, extract:
- Trial name/acronym if mentioned
- Cancer type studied

Return ONLY valid JSON:
{
  "ncts": [
    { "nctId": "NCT12345678", "trialName": "TRIAL_NAME or empty string", "indication": "cancer type studied" }
  ]
}

If no NCT IDs found, return: { "ncts": [] }

Section 14 text:
${textForGemini}`

    const result = await model.generateContent(prompt)
    const responseText = result.response.text()

    // Parse Gemini response — handle markdown code blocks
    let geminiData
    try {
      const jsonMatch = responseText.match(/```(?:json)?\s*([\s\S]*?)```/) || [null, responseText]
      geminiData = JSON.parse(jsonMatch[1].trim())
    } catch (parseError) {
      try {
        geminiData = JSON.parse(responseText.trim())
      } catch {
        return NextResponse.json({ error: 'Failed to parse Gemini response', raw: responseText }, { status: 500 })
      }
    }

    const extractedNcts = geminiData.ncts || []

    return NextResponse.json({
      ncts: extractedNcts,
      section14Length: section14Text.length
    })

  } catch (error) {
    console.error('Extract NCTs error:', error)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

/**
 * Extract Section 14 (Clinical Studies) from DailyMed HTML.
 *
 * DailyMed pages have "14 CLINICAL STUDIES" in both the table of contents (TOC)
 * and the actual body. We need the BODY occurrence, which comes later in the HTML.
 * The body section ends when the next top-level section starts (15, 16, 17, etc.)
 */
function extractSection14(html) {
  // Find ALL occurrences of "14 CLINICAL STUDIES" — we want the LAST one (body, not TOC)
  const pattern = /14\s+CLINICAL\s+STUDIES/gi
  let lastMatch = null
  let match
  while ((match = pattern.exec(html)) !== null) {
    lastMatch = match
  }

  if (lastMatch) {
    const startIdx = lastMatch.index
    const rest = html.substring(startIdx)

    // Find where Section 14 ends — next top-level section header in the body
    // Look for patterns like "15 REFERENCES", "16 HOW SUPPLIED", etc.
    const endMatch = rest.search(
      /(?:^|\s|>)(?:15\s+REFERENCES|16\s+HOW\s+SUPPLIED|17\s+PATIENT\s+COUNSELING|MEDICATION\s+GUIDE)/i
    )
    const endIdx = endMatch > -1 ? endMatch : rest.length

    return stripHtml(rest.substring(0, endIdx))
  }

  // Fallback: look for any div/section containing "CLINICAL STUDIES" heading
  const fallbackMatch = html.match(
    /CLINICAL\s+STUDIES([\s\S]*?)(?=HOW\s+SUPPLIED|REFERENCES|PATIENT\s+COUNSELING)/i
  )
  if (fallbackMatch) {
    return stripHtml(fallbackMatch[1])
  }

  // Last resort: just extract all NCT IDs from the entire page
  const allNcts = html.match(/NCT\d{7,11}/g)
  if (allNcts && allNcts.length > 0) {
    // Build minimal text with NCT contexts
    const uniqueNcts = [...new Set(allNcts)]
    return 'NCT IDs found in document: ' + uniqueNcts.join(', ')
  }

  return null
}

/**
 * For very large Section 14 texts (like OPDIVO with 250K+ chars),
 * truncate intelligently — keep text around each NCT mention and section headers
 */
function truncateKeepingNcts(text, maxLen) {
  // Find all NCT positions
  const nctPattern = /NCT\d{7,11}/g
  const chunks = []
  let match

  while ((match = nctPattern.exec(text)) !== null) {
    // Keep 500 chars of context around each NCT
    const start = Math.max(0, match.index - 300)
    const end = Math.min(text.length, match.index + match[0].length + 200)
    chunks.push(text.substring(start, end))
  }

  // Also keep the first 2000 chars (section headers, trial names)
  const intro = text.substring(0, 2000)

  const combined = intro + '\n...\n' + chunks.join('\n...\n')
  return combined.substring(0, maxLen)
}

/**
 * Strip HTML tags and decode entities, collapse whitespace
 */
function stripHtml(html) {
  return html
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#\d+;/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}
