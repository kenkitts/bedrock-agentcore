# Post Template

Every post in this series follows the same 9-part anatomy. Copy this file when
drafting a new post. Keep sections short; the diff carries the weight.

---

## <Post N> — <Title>

**Primitive:** <AgentCore service, or "none (local)">
**Cumulative tag:** `post-NN-slug`
**Diff from previous:** `git diff post-(N-1)-slug..post-NN-slug`

### 1. Hook / the problem
What limitation of the previous post's agent does this primitive solve?
(e.g., "our agent forgets you the moment the conversation ends.")

### 2. Concept
What the primitive *is*, vendor-neutral, before any AWS specifics. This is the
teaching core — make it land independent of AgentCore.

### 3. How AgentCore does it
The service and its key API/SDK surface. One or two named operations, not a tour.

### 4. Prerequisites + rough cost
- What the reader needs before starting.
- Rough cost to run this post end-to-end. AgentCore is consumption-priced.

### 5. Build it
The code, introduced as a **diff from the previous tag**. Explain each change.

### 6. Run / see it work
A concrete demo with expected output. Show, don't tell.

### 7. Under the hood
The one or two mechanics worth demystifying. Resist explaining everything.

### 8. Clean up
The teardown command(s) for what this post created. Backed by `scripts/teardown_NN_*.sh`.

### 9. Recap + what's next
One paragraph recap; link forward to the next post.

---

### Load-bearing section per post

Not every section is equally important in every post. The plan calls out which
section carries the lesson (e.g., Post 1's *Concept* = the agent loop; Post 7's
*Run* = reading traces). Spend your words there.
