# Agentic Restaurant Review System

Persona-driven **synthetic Yelp-style reviews**: pick a demo user (or define a new cold-start persona), pick a business from the dataset, and the API calls **OpenAI** to produce structured JSON (`rating`, `review`, `reasoning`). Retrieval (FAISS + SentenceTransformers) supplies **style and context hints**; the agent does not invent facts about the target business beyond what is provided.

---

## What you need

| Requirement | Notes |
|-------------|--------|
| **Python 3.12+** | See `.python-version`. |
| **[uv](https://docs.astral.sh/uv/)** | Installs locked deps from `uv.lock`. |
| **OpenAI API key** | Required for `POST /reviews` (persona build + review generation). |
| **Docker** | For `docker compose up`; see [README.Docker.md](README.Docker.md). |


---

## Clone and run locally

```bash
git clone <your-repo-url>
cd Review-System

docker compose up --build
```
More detail: [README.Docker.md](README.Docker.md).



Start the API:

- **Interactive docs (Swagger):** [http://localhost:9000/docs](http://localhost:9000/docs)  
- **ReDoc:** [http://localhost:9000/redoc](http://localhost:9000/redoc)  
- **OpenAPI JSON:** [http://localhost:9000/openapi.json](http://localhost:9000/openapi.json)




---

## Passing your OpenAI API key

### `POST /reviews` (required)

The review endpoint **requires** an HTTP header:

```http
Authorization: Bearer <your_openai_api_key>
```

### cURL example

Replace `YOUR_KEY`, `USER_ID`, and `BUSINESS_ID`:

```bash
curl -X 'POST' \
  'http://localhost:9000/reviews' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
  "business_id": "BUSINESS_ID",
  "user_id": "USER_ID",
  "max_chars":200
}'
```
### Optional env method
Create `.env` if you want defaults for **local scripts**:

```env
AI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
AI_BASE_URL=<Optional Base URL if not using OpenAI. e.g. https://integrate.api.nvidia.com/v1>
```

---

## API overview

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/health/` | No | Liveness: `{"status":"ok"}`. |
| `GET` | `/health/ready` | No | Readiness stub. |
| `GET` | `/users` | No | List all demo `user_id` values (`existing` + `cold_start`). |
| `GET` | `/new-user` | No | JSON Schema + example for **`new_user`** body on `POST /reviews`. |
| `GET` | `/businesses` | No | Paginated businesses (`limit`, `offset`, optional `state`, `city`). |
| `POST` | `/reviews` | **Bearer required** | Generate one structured review. |



---

## `GET /users`

Returns every registered demo user (without full persona blobs). Use a `user_id` from here with `POST /reviews`.

```bash
curl -s "http://127.0.0.1:8000/users"
```


---

## `GET /businesses`

Paginated slice of `businesses.parquet` (stable sort: state, city, business_id).

**Query parameters**

| Param | Default | Description |
|-------|---------|-------------|
| `limit` | `50` | Page size (max `200`). |
| `offset` | `0` | Skip rows. |
| `state` | — | Optional 2-letter US state, e.g. `PA`. |
| `city` | — | Optional exact city string, e.g. `Philadelphia`. |

```bash
curl -s "http://127.0.0.1:8000/businesses?limit=10&offset=0"
```

Response includes `total_matching`, `businesses[]` with `business_id`, `name`, `city`, `state`, etc.

---

## `GET /new-user`

Returns **`json_schema`**, **`example`**, **`nested_field_hints`**, and **`usage`** for the **`new_user`** object accepted by `POST /reviews`. No auth.

```bash
curl -s "http://127.0.0.1:8000/new-user"
```

---

## `POST /reviews`

**Body (JSON)**

| Field | Required | Description |
|-------|----------|---------------|
| `business_id` | Yes | Must exist in `businesses.parquet` and `business_behavior.jsonl`. |
| `user_id` | One of | Existing demo user from `GET /users`. **Mutually exclusive** with `new_user`. |
| `new_user` | One of | Cold-start seed; server creates `api_cold_*` id, appends `test_users.json` + `user_behavior.jsonl`. |
| `max_chars` | No | Soft hint for review length (50–4000). Default **480** if omitted. |


### Example: existing user

```json
{
  "business_id": "Pns2l4eNsfO8kk83dixA6A"
  "user_id": "Hi10sGSZNxQH3NLyWSZ1oA",
}
```

### Example: new cold-start user + `max_chars`

```json
{
  "business_id": "Pns2l4eNsfO8kk83dixA6A",
  "max_chars": 400,
  "new_user": {
    "archetype": "weekend_brunch_seeker",
    "demographics": {
        "city": "Lagos",
        "country": "Nigeria",
        "age_band": "25-34" ,
        "language": "Nigeria English with occasional Pidgin. Uses slangs a lot"
    },
    "preferences": {
      "budget": "mid",
      "cuisines": ["Brunch", "Cafe"],
      "tone": "warm",
      "review_style": "medium-length, practical"
    },
    "service_expectations": {
        "wait_time_tolerance": "medium",
        "price_sensitivity": "medium",
        "portion_size_importance": "high"
    },
    "notes": "Likes natural light and outdoor seating."
  }
}
```

Response shape (simplified):

```json
{
  "user_id": "...",
  "business_id": "...",
  "result": {
    "rating": 4,
    "review": "...",
    "reasoning": {
      "positive_factors": ["..."],
      "negative_factors": ["..."]
    },
    "metadata": {
      "user_id": "...",
      "business_id": "...",
      "max_chars": 400
    }
  }
}
```


## How it works (short)

1. **`ensure_persona_for_test_user`** — If the user has no stored persona in `test_users.json`, an LLM builds one (warm: from Yelp history snippets; cold: from seed + similar users in embedding space).
2. **Retrieval** — User history, business stats/themes, similar businesses, similar reviews (semantic search).
3. **Prompt** — Persona + behaviour JSON + blocks above → OpenAI chat completion with **JSON mode**.
4. **Parse** — Validated into `ReviewGenerationResult`.


---

## Rebuilding data

If you change the Yelp subset:

- **Reviews only:** `python -m app.ingestion.trim_reviews --demo` then `python -m app.retrieval.build_index --only reviews`
- **Full subset from raw JSON:** `python -m app.ingestion.build_subset` (rewrites all Parquet + can refresh `test_users.json`)
- **Behaviour JSONL:** `python -m app.behavior.build_behavior`
- **All FAISS indices:** `python -m app.retrieval.build_index`

After changing Parquet/behaviour, keep **`user_behavior.jsonl`** and **`business_behavior.jsonl`** in sync with `build_behavior`.

---

## Tests

```bash
uv run pytest app/tests/
```

---
