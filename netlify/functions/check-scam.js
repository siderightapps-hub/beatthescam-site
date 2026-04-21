// netlify/functions/check-scam.js
// Proxies scam checker requests to the Anthropic Claude API.
// Set ANTHROPIC_API_KEY in your Netlify environment variables.

exports.handler = async function(event) {
  if (event.httpMethod === "OPTIONS") {
    return {
      statusCode: 200,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
      },
      body: "",
    };
  }

  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method not allowed" };
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error("ANTHROPIC_API_KEY not set");
    return { statusCode: 500, body: JSON.stringify({ error: "Service not configured" }) };
  }

  let message, type;
  try {
    const body = JSON.parse(event.body);
    message = (body.message || "").trim().slice(0, 3000);
    type    = (body.type    || "message").slice(0, 100);
  } catch {
    return { statusCode: 400, body: JSON.stringify({ error: "Invalid request body" }) };
  }

  if (!message || message.length < 5) {
    return { statusCode: 400, body: JSON.stringify({ error: "Message too short" }) };
  }

  const SYSTEM = `You are a UK consumer protection expert specialising in scam detection. You help ordinary people decide whether a message, email, URL, phone call, or job offer is likely to be fraudulent.

Analyse the provided content and respond ONLY with a valid JSON object — no markdown fences, no preamble, no trailing text. Use exactly this structure:

{
  "verdict": "likely_scam" | "possibly_scam" | "probably_legitimate" | "unclear",
  "confidence": "high" | "medium" | "low",
  "summary": "One clear sentence summarising your finding.",
  "red_flags": ["Specific red flag 1", "Specific red flag 2"],
  "green_flags": ["Reassuring sign 1"],
  "recommended_actions": ["Specific action 1", "Specific action 2", "Specific action 3"],
  "reporting_links": [
    {"name": "Action Fraud", "url": "https://www.actionfraud.police.uk/report-a-fraud/report-a-fraud-online"},
    {"name": "Forward to 7726 (SMS spam)", "url": "https://www.ncsc.gov.uk/collection/phishing-scams/report-scam-text-messages"}
  ]
}

Rules:
- red_flags and green_flags must be specific to the content provided, not generic.
- recommended_actions must be concrete and actionable, not generic advice.
- reporting_links should include only UK-relevant links appropriate to the scam type.
- If verdict is probably_legitimate, red_flags may be empty but still list any minor concerns.
- Always include at least one recommended_action even for legitimate messages.
- Do not output anything outside the JSON object.`;

  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 1024,
        system: SYSTEM,
        messages: [
          {
            role: "user",
            content: `Please analyse this ${type}:\n\n${message}`,
          },
        ],
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      console.error("Anthropic API error:", response.status, err);
      return { statusCode: 502, body: JSON.stringify({ error: "Upstream API error" }) };
    }

    const data = await response.json();
    const text = (data.content || []).find(b => b.type === "text")?.text || "";

    // Strip markdown code fences if present (```json ... ``` or ``` ... ```)
    const clean = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "").trim();

    // Validate it's parseable JSON before returning
    let parsed;
    try {
      parsed = JSON.parse(clean);
    } catch {
      console.error("Claude returned non-JSON:", text);
      return { statusCode: 502, body: JSON.stringify({ error: "Invalid response from AI" }) };
    }

    return {
      statusCode: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
      body: JSON.stringify(parsed),
    };
  } catch (err) {
    console.error("Function error:", err);
    return { statusCode: 500, body: JSON.stringify({ error: "Internal error" }) };
  }
};
