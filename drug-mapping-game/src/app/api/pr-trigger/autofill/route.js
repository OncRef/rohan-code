import { NextResponse } from "next/server";
import OpenAI from "openai";

export async function POST(request) {
  try {
    const data = await request.json();
    const { cancer, desc, moa, ncts, pharmClass, sourceLink, approvalDate, brandName, genericName } = data;

    const openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });

    const completion = await openai.chat.completions.create({
      model: "gpt-4o",
      temperature: 0,
      messages: [
        {
          role: "system",
          content: `You are a medical oncology expert AI designed to extract structured drug indication parameters from FDA press release data and prescribing information.

You will receive:
1. defined_cancer (pre-filled or empty)
2. description (raw drug indication text from FDA label)
3. Additional context: mechanism of action, clinical trial references (NCTs), pharmacological class, FDA source link, approval date, brand name, generic name.

Use ALL provided context to produce the most accurate extraction. The press release and prescribing information context helps determine line of therapy, combination partners, biomarker requirements, and trial associations.

If defined_cancer is provided, do not overwrite it. If empty, extract the cancer type from the description.

Extract the following key parameters and return them in structured JSON format:

1. extracted_cancer - The cancer type/subtype. Example: "metastatic colorectal cancer (mCRC) with a BRAF V600E mutation"

2. description - Return the full indication text as provided.

3. line_of_therapy - Identify whether the drug is adjuvant, neoadjuvant, first-line, second-line, or later-line therapy. Use the context about prior treatment requirements and the clinical trial to determine this. Example: "First-Line", "Second-Line", "Adjuvant"

4. previous_tx - Extract any prior treatments patients should have received. If this is a first-line therapy, return "". Example: "Platinum-based chemotherapy"

5. combined_with - Extract drugs used in combination. Include specific chemotherapy regimen names if mentioned in prescribing info. Example: "Cetuximab, Fluorouracil-based chemotherapy (mFOLFOX6 or FOLFIRI)"

6. stage - Cancer stage setting. Example: "Metastatic", "Early-stage", "Locally Advanced", "Unresectable"

7. gene_specificity - Biomarkers, genetic mutations, or receptor statuses required. Example: "BRAF V600E mutation"

8. rair_eligibility - Specific eligibility requirements such as companion diagnostics or regulatory requirements. Example: "As detected by an FDA-authorized test"

9. resection_status - Whether cancer must be resected before treatment. Example: "Resected", "Unresectable", ""

10. other - Additional relevant information including dosage, specific chemotherapy regimens, or notable clinical context not captured above.

11. broad_cancer - An array of one or more broad cancer categories this indication falls under. Choose ONLY from this list:
["Adrenal Cancer and Neuroendocrine Tumors", "Ampullary Adenocarcinoma", "Anal Cancer", "Appendix Cancer", "Bladder Cancer", "Bone and Joint Cancers", "Brain and Other Nervous System", "Breast Cancer", "Castleman Disease", "Colorectal Cancer", "Esophageal Cancer", "Gallbladder Cancer", "Gastric (Stomach) Cancer", "Gastrointestinal Stromal Tumors", "Gestational Cancers", "Gynecological Cancers", "Head and Neck Cancers", "Hematological Malignancies", "Kidney (Renal) and Urethral Cancers", "Liver and Bile Duct Cancers", "Lung Cancers", "Mesothelioma", "Neuroblastoma", "Occult Primary", "Ocular Cancers", "Pancreatic Cancer", "Pediatric Cancers", "Penile Cancer", "Prostate Cancer", "Skin Cancers", "Small Instestine Cancers", "Soft Tissue Cancers (including Heart)", "Specific Syndromes", "Testicular Cancer", "Thymic Cancers", "Thyroid Cancer"]

12. trials - An array of objects with { "sub_cancer": string, "ncts": string }. Map the NCT numbers from context to the relevant cancer sub-type for this indication. If NCTs are provided, include them. Example: [{"sub_cancer": "metastatic colorectal cancer", "ncts": "NCT02928224 (BREAKWATER)"}]

Return ONLY valid JSON with these 12 fields.`,
        },
        {
          role: "user",
          content: `Extract the structured indication fields from the following:

defined_cancer: ${cancer || ''}
description: ${desc || ''}

Additional Context:
- Generic Name: ${genericName || ''}
- Brand Name: ${brandName || ''}
- Mechanism of Action: ${moa || ''}
- Clinical Trial References (NCTs): ${ncts || ''}
- Pharmacological Class: ${pharmClass || ''}
- FDA Source Link: ${sourceLink || ''}
- Approval Date: ${approvalDate || ''}`,
        },
      ],
      response_format: { type: "json_object" },
    });

    const requiredAttributes = [
      "extracted_cancer",
      "description",
      "line_of_therapy",
      "previous_tx",
      "combined_with",
      "stage",
      "gene_specificity",
      "rair_eligibility",
      "resection_status",
      "other",
      "broad_cancer",
      "trials"
    ];

    const jsonResponse = JSON.parse(completion.choices[0].message.content);

    let cleanedResponse = {};
    requiredAttributes.forEach(attr => {
      if (attr === 'broad_cancer') {
        cleanedResponse[attr] = Array.isArray(jsonResponse[attr]) ? jsonResponse[attr] : [];
      } else if (attr === 'trials') {
        cleanedResponse[attr] = Array.isArray(jsonResponse[attr]) ? jsonResponse[attr] : [{ sub_cancer: '', ncts: '' }];
      } else {
        cleanedResponse[attr] = jsonResponse[attr] ?? "";
      }
    });

    return NextResponse.json(cleanedResponse, { status: 200 });
  } catch (e) {
    console.error("Error:", e);
    return NextResponse.json(
      { error: "An error occurred while processing your request." },
      { status: 500 }
    );
  }
}
