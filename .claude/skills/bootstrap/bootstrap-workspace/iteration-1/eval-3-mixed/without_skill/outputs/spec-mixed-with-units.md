# Spec: Full-Stack Task Manager

## Context
Build a task management web app from scratch with a Next.js frontend, Express API backend, and PostgreSQL database. Greenfield project.

## Tech Stack
- Frontend: Next.js 14, TypeScript, Tailwind CSS
- Backend: Express.js, TypeScript
- Auth: JWT-based authentication
- Database: PostgreSQL with Prisma ORM

## Deliverables

1. **Project scaffold** — monorepo with `frontend/` and `backend/` directories, shared `types/` package
2. **`types/index.ts`** — Shared TypeScript interfaces: Task, User, ApiResponse
3. **`backend/prisma/schema.prisma`** — Database schema for users and tasks tables
4. **`backend/src/middleware/auth.ts`** — JWT auth middleware
5. **`backend/src/routes/tasks.ts`** — CRUD API endpoints for tasks (imports from types/ and uses auth middleware)
6. **`backend/src/routes/auth.ts`** — Login/register endpoints (imports from types/, uses Prisma)
7. **`frontend/src/components/TaskList.tsx`** — Task list component with CRUD operations
8. **`frontend/src/components/TaskForm.tsx`** — Create/edit task form
9. **`frontend/src/components/AuthForm.tsx`** — Login/register form
10. **`frontend/src/lib/api.ts`** — API client (imports types from types/)

## Implementation Details

### Shared Types
```typescript
interface Task { id: string; title: string; status: 'todo' | 'in_progress' | 'done'; userId: string; }
interface User { id: string; email: string; name: string; }
interface ApiResponse<T> { data: T; error?: string; }
```

### Database Schema
- Users table: id, email, password_hash, name, created_at
- Tasks table: id, title, description, status, user_id (FK), created_at, updated_at

### Auth Middleware
- Verify JWT from Authorization header
- Attach user to request object
- 401 on invalid/missing token

### API Endpoints
- POST /auth/register, POST /auth/login
- GET /tasks, POST /tasks, PUT /tasks/:id, DELETE /tasks/:id (all require auth)

### Frontend Components
- TaskList: fetches tasks, displays in list, supports status toggle and delete
- TaskForm: controlled form for creating/editing tasks
- AuthForm: login/register with email + password

## Verification
1. `npm install` in both frontend/ and backend/
2. `npx prisma generate` succeeds
3. Backend starts and responds to health check
4. Frontend builds without TypeScript errors
5. Auth flow works end-to-end

## Work Units

### Dependency Graph

```
Unit 1 (Foundation)
  ├──> Unit 2 (Backend: DB + Auth)
  ├──> Unit 3 (Backend: Task Routes)
  └──> Unit 4 (Frontend)
```

Unit 1 must complete first. Units 2, 3, and 4 can then execute in parallel.

---

### Unit 1 — Foundation (must complete first)

**Purpose:** Establish the monorepo scaffold and shared type definitions that all other units import.

**Owned files:**
- `package.json` (root)
- `tsconfig.json` (root, if applicable)
- `types/index.ts`
- `types/package.json`
- `types/tsconfig.json`
- `backend/package.json`
- `backend/tsconfig.json`
- `backend/src/index.ts` (Express app entry point with health-check route)
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/next.config.js`
- `frontend/tailwind.config.ts`
- `frontend/postcss.config.js`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx`

**Deliverables covered:** #1 (project scaffold), #2 (shared types)

**Exit criteria:**
- `npm install` succeeds at the root and in each sub-package.
- `types/index.ts` exports `Task`, `User`, and `ApiResponse<T>` interfaces.
- Backend entry point starts and responds to a health-check endpoint.
- Frontend builds with `next build` (placeholder pages are fine).

---

### Unit 2 — Backend: Database Schema + Auth Routes (parallel)

**Purpose:** Set up the Prisma schema and implement authentication endpoints.

**Owned files:**
- `backend/prisma/schema.prisma`
- `backend/src/middleware/auth.ts`
- `backend/src/routes/auth.ts`

**Depends on:** Unit 1 (imports from `types/`, uses the Express app scaffold and `backend/package.json` dependencies)

**Deliverables covered:** #3 (Prisma schema), #4 (auth middleware), #6 (auth routes)

**Exit criteria:**
- `npx prisma generate` succeeds.
- Auth middleware correctly verifies JWTs and rejects invalid/missing tokens with 401.
- `POST /auth/register` creates a user and returns a JWT.
- `POST /auth/login` authenticates and returns a JWT.

---

### Unit 3 — Backend: Task Routes (parallel)

**Purpose:** Implement CRUD API endpoints for tasks.

**Owned files:**
- `backend/src/routes/tasks.ts`

**Depends on:** Unit 1 (imports from `types/`). Also has a runtime dependency on Unit 2's auth middleware and Prisma schema, but at the code level it only imports `auth.ts` by path and the Prisma client — these imports can resolve as long as Unit 1's scaffold is in place and the files from Unit 2 exist. To keep worktrees independent, Unit 3 should define its own import references and rely on interface contracts rather than Unit 2's implementation. At integration time the files merge cleanly because they own different paths.

**Deliverables covered:** #5 (task CRUD routes)

**Integration note:** This unit imports `../middleware/auth` and uses the Prisma client. During isolated development, stub or mock these imports. At merge time, Unit 2's real implementations slot in with no file conflicts since there is no overlapping file ownership.

**Exit criteria:**
- `GET /tasks` returns tasks for the authenticated user.
- `POST /tasks` creates a task.
- `PUT /tasks/:id` updates a task.
- `DELETE /tasks/:id` deletes a task.
- All endpoints return `ApiResponse<T>` shaped responses.

---

### Unit 4 — Frontend (parallel)

**Purpose:** Build all React components and the API client layer.

**Owned files:**
- `frontend/src/components/TaskList.tsx`
- `frontend/src/components/TaskForm.tsx`
- `frontend/src/components/AuthForm.tsx`
- `frontend/src/lib/api.ts`

**Depends on:** Unit 1 (imports from `types/`, uses the Next.js scaffold)

**Deliverables covered:** #7 (TaskList), #8 (TaskForm), #9 (AuthForm), #10 (API client)

**Exit criteria:**
- `frontend/` builds without TypeScript errors (`next build`).
- `api.ts` exports functions for login, register, and task CRUD, all returning `ApiResponse<T>`.
- `AuthForm` renders login/register with email + password fields.
- `TaskList` renders tasks and supports status toggle and delete.
- `TaskForm` renders a controlled form for creating/editing tasks.

---

### Integration & Merge Order

1. Merge Unit 1 into `main` first.
2. Merge Units 2, 3, and 4 in any order — they own non-overlapping files.
3. After all merges, run the full verification checklist from the spec to confirm end-to-end functionality.
