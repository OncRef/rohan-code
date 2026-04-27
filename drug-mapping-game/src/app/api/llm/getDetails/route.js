import { NextResponse } from "next/server";
import OpenAI from "openai";

export async function POST(request) {
  try {
    // Parse the incoming request body as JSON
    const data = await request.json();
    const { cancer, desc } = data; // Destructure `indication` from the request body

    // Initialize the OpenAI client
    const openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY, // Ensure your API key is stored in environment variables
    });

    // Create a chat completion using OpenAI's API
    const completion = await openai.chat.completions.create({
      model: "gpt-4o", // Use "gpt-4" or "gpt-3.5-turbo" depending on your needs
      messages: [
        {
          role: "system",
          content:
            `You are an AI designed to extract structured drug indication parameters from an input text.
            
            You will receive two inputs:
                1. defined_cancer (pre-filled or empty)
                2. description (raw drug indication text)
            If defined_cancer is provided, do not overwrite it. If defined_cancer is empty, extract the cancer type from the indication_text.
            Return the response in JSON format with structured parameters.
            
            Extract the following key parameters from the provided Indication Text and Defined Cancer and return them in structured JSON format:
            
            Key Fields to Extract (and their corresponding names for JSON):
            1. Defined Cancer (extracted_cancer)
                - If Defined_Cancer is provided, keep it as is.
                - If Defined_Cancer is empty or "", extract the cancer type from the text.
                - Example: "Adjuvant Breast Cancer", "Metastatic Non-Small Cell Lung Cancer"
            
            2. Description (description)
                - Return the full indication text as provided in the input.
            
            3. Line of Therapy (line_of_therapy)
                - Identify whether the drug is adjuvant, neoadjuvant, first-line, second-line, or later-line therapy.
                - Example: "Adjuvant", "First-Line", "Second-Line"
            
            4. Previously Treated With (previous_tx)
                - Extract any prior treatments that patients should have received before starting this drug. If none are mentioned, return "".
                - Example: "Platinum-based chemotherapy", ""
            
            5. In Combination With (combined_with)
                - Extract the list of drugs used in combination with this drug. If none, return "".
                - Example: ["Doxorubicin", "Cyclophosphamide", "Paclitaxel", "Docetaxel"]
            
            6. Stage (stage)
                - Identify whether the cancer is in early-stage, locally advanced, or metastatic settings. If not specified, return "".
                - Example: "Early-stage", "Metastatic", "Locally Advanced"
            
            7. Gene / Biomarker Positive Mentioned (gene_specificity)
                - Extract any biomarkers, genetic mutations, or receptor statuses required for eligibility.
                - Example: "HER2-overexpressing node positive or node negative (ER/PR negative or with one high-risk feature)"
            
            8. RAIR Eligibility (rair_eligibility)
                - Identify any specific eligibility requirements such as companion diagnostics, regulatory approvals, or prior therapies.
                - Example: "FDA-approved companion diagnostic for trastuzumab"
            
            9. Resection Status (resection_status)
                - If applicable, determine whether the cancer must be resected before treatment. If not specified, return "".
                - Example: "Resected", "Unresectable", ""
            
            10. Other (other)
                - Any additional relevant information that does not fit into the above categories.
                - Example: "Considered for patients with contraindications to platinum-based chemotherapy."`,
        },
        {
          role: "user",
          content: `Extract the fields from the information below:
          defined_cancer: ${cancer}
          description: ${desc}`,
        },
      ],
      response_format: { type: "json_object" }, // Enforce JSON response
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
      "other"
    ];

    // Parse the response content as JSON
    const jsonResponse = JSON.parse(completion.choices[0].message.content);
    // console.log(jsonResponse);

    let cleanedResponse = {};
    requiredAttributes.forEach(attr => {
      cleanedResponse[attr] = jsonResponse[attr] ?? "";
    });

    // Return the JSON response
    return NextResponse.json(cleanedResponse, { status: 200 });
  } catch (e) {
    console.error("Error:", e); // Log the error for debugging
    return NextResponse.json(
      { error: "An error occurred while processing your request." }, // Return a user-friendly error message
      { status: 500 } // Use 500 for server errors
    );
  }
}