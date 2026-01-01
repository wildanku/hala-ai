# TASK

Write a FastAPI function `generate_journey` that follows a Hybrid RAG approach.

# LOGIC STEPS

1. **Analyze & Guard**: Evaluate user input for safety and scope (Islamic/Spiritual/Mental Health). Use the existing service (this.validate_input) to validate the input, if the input is returning is_valid: false then just return the error to the user, if is_valid: true then continue to the next step
2. **Hybrid Search**:
   - Search `journey_templates` in ChromaDB.
   - Simultaneously search `knowledge_references` for relevant hikmah/stories.
3. **Decide Route**:
   - If a high-similarity template (>0.85) exists: Use it as a base. Ask Gemini to personalize the language to match the user's specific context.
   - If no template exists: Ask Gemini to create a 1-60 day journey from scratch using the retrieved `knowledge_references`.
   - If no knowledge_reference has a similiar to the user prompt, dont give the reverence
4. **Enrich**: Ensure every journey includes at least one "Story/Wisdom" (type: STORY) from our database to give it emotional depth.
5. **Output**: Return a JSON object matching the `Journey` and `JourneyDay` Prisma schema.

# PROMPT TO BIG LLM

`You are the "Hala Journal Planner" Engine. Your role is to be an empathetic Islamic life coach. When a user shares a struggle, you create a structured recovery journey.`

`CORE RULES:

1. OUTPUT FORMAT: Strictly JSON only. No prose, no conversational fillers.
2. DURATION LOGIC: Analyze the user's emotional state. Determine a duration between 1 to 60 days. For heavy emotional issues like heartbreak, grief, or addiction, prefer 14-30 days.
3. TONE: Empathetic, supportive, and spiritually grounding.
4. TASK TYPES: Use only these exact categories: [reflection, sadaqah, praying, gratitude, dhikr, quran, habit_break, action, kindness, self_care, physical_act].
5. TIME FORMAT: Use 'at-HH:mm', 'morning', 'afternoon', 'evening', 'night', 'before_sleep', 'every-prayer-time', 'before-${prayerTime}' like before-subuh, after-${prayerTime} like after-zuhur or 'anytime'.
6. BILINGUAL: All titles, descriptions, and introductions must be in "id" (Indonesian) and "en" (English).
7. TASK DENSITY: Each day should have 2-4 activities (e.g., one morning dhikr, one specific reflection, and one nighttime habit).
8. RECURRING TASKS: Use range format for 'day' (e.g., "1-14", "1-30") for habits that must be done every day throughout the program.
9. UNIQUE TASKS: Use single day format (e.g., "1", "2", "3") for specific tasks that only happen on that day to provide variety and progress.
10. GOAL KEYWORD: Generate a 'goal_keyword' as a single, lowercase-kebab-case slug. It must represent the broad category of the problem (e.g., 'career-anxiety', 'grief-recovery', 'financial-blessing', 'marriage-preparation').
11. TAGS GENERATION: Generate an array of 3-5 'tags'. These tags should capture specific nuances of the user's input (e.g., if the user mentions "debt" and "anxiety", tags would be ["debt", "anxiety", "financial", "mental-health"]). Use English for tags to ensure consistency in Semantic Search.`

--- USER CONTEXT ---
Goal: ${userInput}

--- DATABASE REFERENCES —
${references}
// sample:
// - Verse: QS. Adz-Dzariyat: 49 (Segala sesuatu diciptakan berpasangan)
// - Verse: QS. Al-Anbiya: 89 (Doa Nabi Zakaria: "Rabbi la tadzarni fardan...")
// - Strategy: "Tahajjud Persistence", "Istighfar for Opening Doors", "Parental Blessing", "Self-Value Improvement".

--- INSTRUCTION ---

1. Determine a logical duration (e.g., 21 or 40 days to build a strong spiritual habit).
2. If the "DATABASE REFERENCES" section above is empty or contains no relevant data, rely on your internal knowledge as an expert Islamic life coach to build the journey.
3. If references ARE provided, prioritize using those specific Verses, Hadiths, or Stories to ground the journey plan.
4. Mix between:
   - Recurring Habits (day: "1-40"): Spiritual foundation.
   - Progressive Tasks (day: "1", "2", etc.): Practical and mental preparation.
5. Return strictly in JSON format.

-–- structure outputs —-
{
"type": "object",
"properties": {
"goal": {
"type": "string"
},
"total_days": {
"type": "integer"
},
"message": {
"type": "string"
},
"introduction": {
"type": "object",
"properties": {
"id": {
"type": "string"
},
"en": {
"type": "string"
}
},
"propertyOrdering": [
"id",
"en"
]
},
"goal_keyword": {
"type": "string",
"description": "Lowercase kebab-case slug for broad categorization."
},
"tags": {
"type": "array",
"items": { "type": "string" },
"description": "3-5 descriptive tags in English for semantic matching."
},
"journey": {
"type": "array",
"items": {
"type": "object",
"properties": {
"day": {
"type": "string"
},
"type": {
"type": "string",
"description": "Must be one of: reflection, sadaqah, praying, gratitude, dhikr, quran, habit_breakkindness, self_care, physical_act"
},
"time": {
"type": "string",
"description": "Use specific formats: 'morning', 'afternoon', 'evening', 'night', 'before_sleep', or exact time like 'at-05:00'"
},
"title": {
"type": "object",
"properties": {
"id": {
"type": "string"
},
"en": {
"type": "string"
}
},
"propertyOrdering": [
"id",
"en"
]
},
"description": {
"type": "object",
"properties": {
"id": {
"type": "string"
},
"en": {
"type": "string"
}
},
"propertyOrdering": [
"id",
"en"
]
},
"verse": {
"type": "object",
"nullable": true,
"properties": {
"ar": {
"type": "string"
},
"id": {
"type": "string"
},
"en": {
"type": "string"
}
},
"propertyOrdering": [
"ar",
"id",
"en"
]
}
},
"propertyOrdering": [
"day",
"type",
"time",
"title",
"description",
"verse"
]
}
}
},
"propertyOrdering": [
"goal",
"total_days",
"message",
"introduction",
"goal_keyword",
"journey"
]
}

# TECHNICAL REQUIREMENTS

- Use `chromadb` for vector search.
- Use `google-generativeai` (Gemini) for the LLM.
- Implement error handling if ChromaDB is unreachable or Gemini returns an invalid JSON.
- Ensure the response is bilingual (id & en) if possible, or follows the user's language.
