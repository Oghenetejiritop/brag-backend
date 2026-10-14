
/**
 * BRAG external chatbot integration example.
 *
 * Run using Node.js 18 or later.
 * This example is intended for a trusted server-side
 * environment, not browser-side React code.
 */

const API_BASE_URL =
  process.env.BRAG_API_BASE_URL ??
  "http://127.0.0.1:8000";

const API_KEY = process.env.BRAG_API_KEY;
const CHATBOT_ID = process.env.BRAG_CHATBOT_ID;

async function main() {
  if (!API_KEY || !CHATBOT_ID) {
    throw new Error(
      "Set BRAG_API_KEY and BRAG_CHATBOT_ID first."
    );
  }

  const endpoint =
    `${API_BASE_URL}/api/v1/chatbots/${CHATBOT_ID}/query`;

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question:
        "What is the special test phrase in the uploaded document?",
    }),
  });

  if (!response.ok) {
    throw new Error(
      `BRAG request failed: HTTP ${response.status}`
    );
  }

  const result = await response.json();

  console.log("Chatbot ID:", result.chatbot_id);
  console.log("Answer:", result.answer);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
