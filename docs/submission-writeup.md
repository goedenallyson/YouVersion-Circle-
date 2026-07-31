# YouVersion Circle

## A Scripture experience that listens, learns, and helps communities reflect together

YouVersion Circle is an additional feature designed to extend the existing YouVersion Bible experience into ongoing, group-centered Scripture engagement. Rather than asking users to adopt another Bible application or chatbot, Circle integrates with communities they already belong to—such as Bible studies, friend groups, or church communities—and helps them remain spiritually connected between in-person gatherings.

Each day, members of a Circle receive the same Scripture passage, retrieved live through the YouVersion Platform API, and a shared reflection prompt. Members may highlight a phrase that stands out and respond with an emotion, a single word, or a brief reflection. Responses remain hidden until each participant contributes their own perspective, encouraging independent thought and reducing the likelihood that early responses will influence the rest of the group.

This interaction model is informed by the Nominal Group Technique, a structured approach in which participants first generate ideas independently before those ideas are collected, clarified, and grouped. In YouVersion Circle, members complete the individual idea-generation stage, while Gloo AI Studio supports the aggregation and clarification stages. Once a member responds, the Group Pulse unlocks. The AI identifies common themes, needs, or expressions of praise and produces a concise pastoral summary alongside the group’s named responses. This creates opportunities for members to pray, offer support, and continue conversations outside their scheduled meetings.

Circle also includes a “Recommended for Your Group” engine. Engagement signals from the group’s responses are structured, classified, weighted, and aggregated to identify candidate passages for the following day. Candidate passages are validated for contextual relevance, appropriate length, safety, and repetition before the next passage is selected and stored. Safeguards ensure that AI-generated insights are clearly distinguished from Scripture and that Gloo AI supports—not replaces—pastoral or spiritual leadership.

Technically, the prototype uses a FastAPI backend exposing an API endpoint. It retrieves Scripture from YouVersion using the App Key authentication and the BSB translation. Gloo AI Studio is accessed through OAuth2 client credentials and the /ai/v2/chat/completions endpoint, with auto_routing used for model selection. The frontend is built with React, Vite, and TypeScript. All credentials remain server-side, and the frontend communicates only with the Circle backend.

The path to production includes persistent storage, authenticated user accounts, push notifications, and integration with YouVersion. The central feedback loop remains consistent: a group’s shared spiritual posture helps shape the Scripture it engages with next.
