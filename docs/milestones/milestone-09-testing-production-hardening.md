# Milestone 9 — Testing & Production Hardening

> **Phase:** Phase 4 — Quality & Reliability  
> **Status:** In Progress

---

## Objective

Implement comprehensive automated testing (unit, integration, component) and harden the application for production deployment without changing core architecture or functionality. Ensure code reliability, API contract validation, and user-facing error handling.

---

## Why

Milestones 2–8 delivered a feature-complete MVP, but without automated tests:

1. **No regression detection** — Code changes risk breaking existing features silently
2. **No confidence in refactoring** — Debt accumulation goes unnoticed
3. **Production unsuitable** — Unvalidated API contracts fail in real environments
4. **No evidence of correctness** — Manual testing is non-reproducible and incomplete
5. **Debugging friction** — Production bugs require guesswork instead of test-driven diagnosis

This milestone adds the safety net needed before deployment and serves as executable documentation for future developers.

---

## How

### Testing architecture

```text
┌─────────────────────────────────────────────────────┐
│         Automated Test Suite (CI-Ready)             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Unit Tests (pytest)          Frontend Tests (Jest) │
│  ├─ rag_service.py            ├─ Login Component   │
│  ├─ vector_store.py           ├─ Upload Form       │
│  ├─ qa_service.py             ├─ Chat Interface    │
│  └─ config.py                 └─ Citations Modal   │
│                                                     │
│  Integration Tests (pytest-asyncio)                │
│  ├─ POST /documents/upload                         │
│  ├─ GET /documents                                 │
│  ├─ POST /search                                   │
│  ├─ POST /ask (with chat history)                  │
│  └─ POST /auth/login                               │
│                                                     │
│  E2E Validation (manual + future automation)       │
│  ├─ Upload PDF → Search → Ask workflow             │
│  ├─ Multi-document scenarios                       │
│  └─ Error recovery paths                           │
│                                                     │
└─────────────────────────────────────────────────────┘

Test Coverage Target: 80%+ on backend services and routers
```

### Phase 1: Backend Unit Tests

**Goal:** Verify individual service functions behave correctly in isolation.

**Approach:**
1. Mock all Gemini API calls (embedding and generation)
2. Test success paths (happy path)
3. Test error paths (invalid inputs, empty collections)
4. Test edge cases (large documents, malformed PDFs)

**Services to test:**
- `rag_service.py` — PDF extraction, chunking, error handling
- `vector_store.py` — Embedding, ChromaDB operations, retrieval
- `qa_service.py` — Query condensing, prompt building, answer generation

### Phase 2: API Integration Tests

**Goal:** Verify endpoints work end-to-end with real service calls (mocked Gemini).

**Approach:**
1. Use `pytest-asyncio` for async endpoint testing
2. Create test fixtures (sample PDFs, test collections)
3. Verify request validation (type checking, field constraints)
4. Verify response models (correct structure, required fields)
5. Verify authentication (token checking on protected routes)
6. Verify error responses (HTTP status codes, error messages)

**Endpoints to test:**
- `POST /auth/login` — Success, invalid password, missing fields
- `POST /documents/upload` — Valid PDF, invalid file type, no auth, oversized file
- `GET /documents` — With/without documents, auth required
- `GET /documents/stats` — Collection state consistency
- `POST /search` — Valid query, empty collection, invalid top_k bounds
- `POST /ask` — With/without chat history, no context available, auth required

### Phase 3: Frontend Component Tests

**Goal:** Verify React components render and respond to user interaction correctly.

**Approach:**
1. Use React Testing Library (behavior-driven, not implementation-driven)
2. Test visible outputs (rendered text, form inputs)
3. Test user interactions (button clicks, form submissions)
4. Mock Fetch API for backend calls
5. Test loading/error states

**Components to test:**
- **Login page** — Render form, submit credentials, handle errors
- **Upload form** — File selection, disabled state, success/error feedback
- **Chat input** — Text entry, top_k slider, disabled while loading
- **Message display** — User/assistant bubbles, source citation button
- **Citations modal** — Render sources, close on background click
- **Document list** — Render indexed documents, show metadata, refresh

### Phase 4: Production Hardening (Code Changes, No Architecture Redesign)

**Goal:** Improve reliability without changing how the application works.

**Changes:**
1. **Exception handling** — Catch broad exceptions, provide specific error messages
2. **Logging** — Add debug/info/warning levels for troubleshooting
3. **Retry logic** — Retry Gemini API calls (exponential backoff, max 3 attempts)
4. **Input validation** — Stricter type/range checking in routers
5. **Code cleanup** — Remove dead code, consolidate duplicate patterns
6. **Security defaults** — Harden auth, validate file uploads, sanitize responses

**No changes to:**
- API endpoints or response structures
- Frontend UI or components
- Document processing pipeline
- Embedding/generation models
- ChromaDB integration

### Phase 5: Testing Documentation

**Goal:** Document the testing strategy for future developers.

**Contents (`docs/testing.md`):**
- Test suite architecture
- How to run tests locally and in CI
- Coverage reporting
- Mock strategy (why, what, how)
- Adding new tests
- Known limitations
- Future test improvements

---

## Where

### Files created

| File | Role |
|------|------|
| `backend/tests/__init__.py` | Makes `tests` a Python package |
| `backend/tests/conftest.py` | Shared pytest fixtures (mocks, test data) |
| `backend/tests/unit/test_rag_service.py` | Unit tests for rag_service |
| `backend/tests/unit/test_vector_store.py` | Unit tests for vector_store |
| `backend/tests/unit/test_qa_service.py` | Unit tests for qa_service |
| `backend/tests/unit/__init__.py` | Unit tests package |
| `backend/tests/integration/test_api.py` | API endpoint integration tests |
| `backend/tests/integration/__init__.py` | Integration tests package |
| `frontend/src/__tests__/App.test.jsx` | React component tests |
| `frontend/src/__tests__/setup.js` | Jest configuration and mocks |
| `docs/testing.md` | Testing strategy documentation |

### Files modified

| File | Change |
|------|--------|
| `backend/requirements.txt` | Add pytest, pytest-asyncio, pytest-cov, pytest-mock |
| `frontend/package.json` | Add @testing-library/react, @testing-library/jest-dom, vitest |
| `backend/services/qa_service.py` | Improve error handling, add logging |
| `backend/services/rag_service.py` | Add retry logic for Gemini calls, improve logging |
| `backend/services/vector_store.py` | Add exception handling, improve validation |
| `backend/api/*.py` | Improve validation and error responses (all routers) |
| `.gitignore` | Ignore test coverage reports (`.coverage`, `htmlcov/`) |

### Project structure after completion

```
Enterprise-RAG/
├── backend/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                    # Shared fixtures
│   │   ├── unit/
│   │   │   ├── __init__.py
│   │   │   ├── test_rag_service.py
│   │   │   ├── test_vector_store.py
│   │   │   └── test_qa_service.py
│   │   └── integration/
│   │       ├── __init__.py
│   │       └── test_api.py
│   ├── api/
│   ├── services/
│   ├── core/
│   ├── uploads/
│   ├── chroma_db/
│   ├── main.py
│   └── requirements.txt                  # Updated with test deps
├── frontend/
│   ├── src/
│   │   ├── __tests__/
│   │   │   ├── App.test.jsx
│   │   │   └── setup.js
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   └── package.json                      # Updated with test deps
├── docs/
│   ├── milestones/
│   │   └── milestone-09-testing-production-hardening.md
│   └── testing.md                        # NEW
└── .gitignore                            # Updated
```

---

## Implementation strategy

### Phase 1: Backend Unit Tests (3–4 days)

**Step 1:** Configure pytest
- Install `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`
- Create `backend/tests/conftest.py` with shared fixtures
- Set up coverage reporting in `pytest.ini`

**Step 2:** Mock Gemini API
- Create fixtures that mock `GoogleGenerativeAI` calls
- Return realistic embedding vectors (768 dims)
- Return realistic generation responses

**Step 3:** Write unit tests
- `test_rag_service.py` — Test extraction, chunking, error paths
- `test_vector_store.py` — Test embeddings, storage, retrieval
- `test_qa_service.py` — Test query condensing, prompt building

**Step 4:** Achieve 80%+ coverage
- Run `pytest --cov=backend/services`
- Fill gaps until 80%+ coverage

### Phase 2: API Integration Tests (2–3 days)

**Step 1:** Create test fixtures
- Sample PDF for testing
- Test ChromaDB collection (separate from dev collection)
- Test auth token

**Step 2:** Write integration tests
- Test happy path for each endpoint
- Test error paths (invalid input, missing auth, etc.)
- Test response model validation

**Step 3:** Verify request/response contracts
- Ensure all endpoint responses match documented models
- Test field constraints (min/max values, required fields)
- Test error response format

### Phase 3: Frontend Component Tests (2–3 days)

**Step 1:** Configure Jest + React Testing Library
- Install `@testing-library/react`, `@testing-library/jest-dom`
- Create `frontend/src/__tests__/setup.js` for mock configuration
- Mock Fetch API globally

**Step 2:** Write component tests
- Test login form submission
- Test document upload form
- Test chat message sending
- Test loading/error states
- Test citation modal display

**Step 3:** Focus on user behavior
- Test what user sees, not component internals
- Mock backend API calls
- Verify rendered output and user feedback

### Phase 4: Production Hardening (2–3 days)

**Step 1:** Review and improve backend services
- Add try/catch blocks where missing
- Add structured logging (debug, info, warning)
- Add input validation before processing
- Add retry logic for Gemini API failures (3 attempts, exponential backoff)

**Step 2:** Review and improve API routers
- Improve validation error messages
- Ensure all endpoints return consistent error format
- Add rate limiting considerations (document for future)

**Step 3:** Clean up code
- Remove debug print statements
- Consolidate duplicate code patterns
- Add comments for complex logic
- No architectural changes — only improvements to existing code

### Phase 5: Documentation (1–2 days)

**Step 1:** Create `docs/testing.md`
- Overview of test architecture
- Folder structure explanation
- How to run tests locally
- How to interpret coverage reports
- Mock strategy and why it matters

**Step 2:** Add comments to test files
- Explain test purpose at module level
- Explain complex mock setups
- Link to corresponding implementation code

---

## Technologies & tools

| Tool | Purpose | Version |
|------|---------|---------|
| pytest | Python unit testing | 7.x+ |
| pytest-asyncio | Test async functions | 0.21.x+ |
| pytest-cov | Coverage reporting | 4.x+ |
| pytest-mock | Fixtures for mocking | 3.x+ |
| @testing-library/react | React component testing | 14.x+ |
| @testing-library/jest-dom | DOM matchers | 6.x+ |
| jest | JavaScript test runner | (via Vitest config) |
| unittest.mock | Python mock module | builtin |
| google.generativeai | Gemini API (mocked) | mock imports only |

---

## Key design decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Backend test framework | pytest | De facto standard for Python; async support via pytest-asyncio |
| Frontend test framework | React Testing Library | Tests user behavior, not implementation; reduces brittle tests |
| Mocking strategy | Mock at function entry points | Avoids network calls; fast test execution |
| Gemini mock data | Realistic vectors + responses | Ensures tests don't pass with fake data |
| Test coverage target | 80%+ | Covers critical paths; practical (not 100%) |
| Separate test collection | Yes (Chroma isolation) | Dev collection untouched; tests independent |
| CI/CD implementation | Out of scope | Manual test runs only; CI added in future milestone |
| Refactoring scope | Code quality only | No architecture redesign; preserve existing behavior |

---

## Acceptance criteria

### Phase 1: Backend Unit Tests
- ✅ All service functions tested for success and error paths
- ✅ Gemini API completely mocked (no real API calls in tests)
- ✅ Coverage report shows 80%+ for `backend/services/`
- ✅ All tests pass with `pytest --cov`
- ✅ No integration tests yet (unit tests only)

### Phase 2: API Integration Tests
- ✅ All 6 endpoints tested (auth, upload, search, ask, docs, stats)
- ✅ Request validation tested (type errors, bounds, required fields)
- ✅ Response models validated (structure, field types)
- ✅ Authentication validated on protected routes
- ✅ Error responses return HTTP 400/401/500 with proper format
- ✅ Coverage report shows 80%+ for `backend/api/`

### Phase 3: Frontend Component Tests
- ✅ Login component renders and submits
- ✅ Upload form handles file selection and submission
- ✅ Chat interface handles user input and shows loading state
- ✅ Error states display error messages correctly
- ✅ Citations modal opens/closes and displays sources
- ✅ All tests use React Testing Library (no snapshot tests)

### Phase 4: Production Hardening
- ✅ All external API calls wrapped in try/catch
- ✅ Structured logging added to all services
- ✅ Retry logic added to Gemini API calls (max 3, exponential backoff)
- ✅ Input validation improved in all routers
- ✅ Error messages are user-friendly (no stack traces in responses)
- ✅ Existing tests still pass (no behavior changes)
- ✅ No architectural changes

### Phase 5: Documentation
- ✅ `docs/testing.md` created with complete testing guide
- ✅ Test files have docstrings explaining purpose
- ✅ Mock strategy documented
- ✅ Coverage reports instructions included
- ✅ Future testing improvements listed

---

## Testing strategy

### Unit tests
- **Scope:** Individual functions in services
- **Mocking:** All external API calls (Gemini, ChromaDB where applicable)
- **Speed:** < 100ms per test (fast feedback)
- **Purpose:** Verify logic correctness in isolation

### Integration tests
- **Scope:** API endpoints with mocked services
- **Mocking:** Gemini API only (use real ChromaDB for test collection)
- **Speed:** < 500ms per test
- **Purpose:** Verify contracts between components

### Component tests
- **Scope:** React components with user interactions
- **Mocking:** Fetch API (backend calls)
- **Speed:** < 200ms per test
- **Purpose:** Verify UI renders and responds correctly

### E2E validation (manual, not automated yet)
- **Scope:** Full workflow (upload → search → ask)
- **Mocking:** None (real backend)
- **Speed:** Minutes (manual)
- **Purpose:** Ensure real-world usage works

---

## Common mistakes to avoid

### ❌ Testing implementation details
- ✅ **Instead:** Test visible behavior (what user sees, not how it works)
- Example: Don't test that `setQuery` was called; test that input value changed

### ❌ Mocking too much or too little
- ✅ **Instead:** Mock only external dependencies (API calls); test real code paths
- Example: Mock Gemini API, but use real ChromaDB for integration tests

### ❌ Brittle snapshot tests
- ✅ **Instead:** Test specific output properties, not entire rendered output
- Example: Check that button text is "Send Message", not snapshot of HTML

### ❌ Tests that depend on execution order
- ✅ **Instead:** Make tests independent; use fixtures for setup/teardown
- Example: Don't rely on test A to upload PDF for test B; each test uploads independently

### ❌ Tests that pass by accident
- ✅ **Instead:** Verify mock data matches reality
- Example: If mocking embedding dimensions, ensure 768 (not fake small number)

### ❌ No coverage reporting
- ✅ **Instead:** Run coverage checks regularly; track coverage trends
- Example: `pytest --cov=backend/services --cov-report=html`

### ❌ Changing production code to pass tests
- ✅ **Instead:** Change tests if requirements change; keep production code behavior unchanged
- Example: Don't add `if test_mode` flags in production code

---

## Expected outcomes

### After Phase 1 (Backend Unit Tests)
- 50+ unit tests written
- 80%+ coverage of `backend/services/`
- Developers confident in service logic
- Fast feedback on regressions

### After Phase 2 (API Integration Tests)
- 30+ integration tests written
- All endpoint contracts validated
- API documentation verified
- Request/response format guaranteed

### After Phase 3 (Frontend Tests)
- 20+ component tests written
- User workflows verified
- Error states handled
- Accessibility checks in place

### After Phase 4 (Production Hardening)
- Exception handling comprehensive
- Logging actionable and structured
- Retry logic resilient
- Input validation strict
- Code is production-ready

### After Phase 5 (Documentation)
- Testing strategy documented
- New developers can run tests immediately
- Coverage targets clear
- Future improvements planned

---

## Future improvements (out of scope for Milestone 9)

1. **CI/CD pipeline** — Automated test runs on every commit (GitHub Actions, GitLab CI)
2. **Load testing** — Verify performance under concurrent users
3. **Security testing** — Penetration testing, input injection tests
4. **Performance profiling** — Identify bottlenecks and optimize
5. **E2E automation** — Selenium/Cypress for browser automation
6. **Visual regression testing** — Screenshot comparisons for UI changes
7. **API contract validation** — Pact testing for breaking changes
8. **Database migration testing** — Test ChromaDB upgrades
9. **Monitoring & observability** — Production telemetry and alerting
10. **Accessibility testing** — WCAG compliance verification

---

## How to test this milestone

### Manual verification

1. **Phase 1 complete:** Run `pytest backend/tests/unit/ --cov=backend/services/`
   - Verify all tests pass
   - Verify coverage > 80%

2. **Phase 2 complete:** Run `pytest backend/tests/integration/ --cov=backend/api/`
   - Verify all tests pass
   - Verify endpoints respond correctly

3. **Phase 3 complete:** Run `npm test` from `frontend/` directory
   - Verify all component tests pass
   - Verify no console errors

4. **Phase 4 complete:** 
   - Review backend service code for exception handling
   - Check that logging is present in error paths
   - Start backend and verify error messages are user-friendly

5. **Phase 5 complete:**
   - Read `docs/testing.md`
   - Verify instructions are clear and complete
   - Test that examples work as documented

### Automated verification

- CI/CD pipeline (future) will run all tests on every commit
- Coverage badges will display on project README
- Test failures will block deployment

---

## What's next

**Milestone 10 — Security Hardening & API Documentation (Future):**

Once testing is in place and the application is proven reliable:

1. Replace mock authentication with real JWT/OAuth
2. Add password hashing (bcrypt)
3. Generate OpenAPI spec from FastAPI
4. Document all endpoints with examples
5. Security audit for OWASP Top 10
6. Add input sanitization where needed

Then production deployment becomes feasible.
