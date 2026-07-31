# YouVersion Circle — Submission for Scripture in New Frontiers

Hi, I'm excited to introduce YouVersion: Circle, our submission for Scripture in New Frontiers.

The original challenge asks us to imagine new ways to combine YouVersion's Bible content with Gloo AI Studio. We decided to answer that challenge by turning the familiar verse of the day experience from YouVersion into something more relational, adaptive, and group-centered.

What if the Verse of the Day you saw was specifically picked for you and your community? What if these Scriptures could meet you uniquely where you are?

Here's the vision: Every day you and your community receive an engaging Scripture passage to drive the community deeper in relationship, not only with each other but with the Lord.

Each day members read the passage, highlight a word or phrase that stands out, and are prompted with a short engagement that is either a reflection sentence or word or as simple as naming the current emotion they are feeling.

---

## Read + Engage

The first screen presents a passage chosen for the group. Users highlight what stands out and complete one daily prompt (an emotion tap, a short reflection, or a single word). This is lightweight by design — consistency matters more than depth.

---

## Group Pulse

Once the user responds, the Group Pulse unlocks. This is where Gloo AI Studio synthesizes the responses across the group and names the pulse of the moment. It can recognize whether the group is expressing a need, a praise, a shared theme, or a recurring concern.

Users see this insight along with the direct responses of their community. Allowing for opportunity to connect directly or intentionally pray for others.

For example:
- If several people highlight language around peace and write about anxiety, Gloo AI may identify anxiety as the group's top need today.
- If the group is responding with gratitude and encouragement, the summary shifts toward praise.

The AI is not replacing Scripture or spiritual leadership. It is helping the group notice patterns in how they are responding to Scripture together.

---

## Recommended for Your Group

Unknown to users, Circle uses a Recommended for Your Group feature that is based on prior engagement to suggest future Scripture. Gloo AI helps interpret the signals — taking reflections, highlights, themes, needs, praises to search within YouVersion Bible text for tomorrow's Scripture.

Our implemented Safeguards prevent one person's response from defining the whole group, it avoids repetition, and it ensures AI insight is never presented as Scripture.

---

## Architecture & Vision

YouVersion Circle includes a FastAPI backend in a lightweight package. Our vision for this project is to be plugged into the current YouVersion Bible app, not as a standalone. This allows Gloo and YouVersion to utilize their pre-existing platforms instead of gathering engagement somewhere new.

The long-term vision is simple: YouVersion Circle helps groups move from daily Bible reading to daily shared rhythms. It keeps Scripture central, uses AI responsibly, and creates a feedback loop where a group's real spiritual posture shapes what they see next.

YouVersion Circle is not just a smarter Verse of the Day. It is a Scripture experience that listens, learns, and helps communities reflect together.
