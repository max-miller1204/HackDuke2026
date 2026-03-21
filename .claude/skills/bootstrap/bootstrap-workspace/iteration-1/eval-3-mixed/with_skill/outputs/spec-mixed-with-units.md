# Spec: Full-Stack Task Manager

## Context
Build a task management web app from scratch with a Next.js frontend, Express API backend, and PostgreSQL database. Greenfield project.

## Tech Stack
- Frontend: Next.js 14, TypeScript, Tailwind CSS
- Backend: Express.js, TypeScript
- Database: PostgreSQL with Prisma ORM
- Auth: JWT-based authentication

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

---

## Work Units

### Execution Strategy
Foundation → Parallel (concurrent worktrees)

**Rationale:** The project has clear foundation work (scaffold, shared types, Prisma schema, auth middleware) that multiple deliverables depend on. Once foundation is in place, the remaining work splits into three units with no file overlaps and no runtime/import dependencies between them. Backend task routes and backend auth routes do not import from each other. Frontend components communicate with the backend via HTTP at runtime, not via direct imports, so they are independent of backend route code. All three parallel units depend only on foundation outputs (shared types, Prisma client, auth middleware).

### Foundation Unit (Phase 1)

**Files:**
- Create: `package.json` (root monorepo config)
- Create: `types/index.ts`
- Create: `types/package.json`
- Create: `backend/package.json`
- Create: `backend/tsconfig.json`
- Create: `backend/prisma/schema.prisma`
- Create: `backend/src/middleware/auth.ts`
- Create: `backend/src/index.ts` (Express app entry point with health check)
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`

**Tasks:**
- Initialize monorepo with root `package.json` and workspace configuration for `types/`, `backend/`, and `frontend/`
- Create shared `types/index.ts` with Task, User, and ApiResponse interfaces
- Create Prisma schema with Users and Tasks tables, including the user_id foreign key relationship
- Implement JWT auth middleware that verifies tokens from the Authorization header, attaches user to the request, and returns 401 on invalid/missing tokens
- Set up Express app entry point with health check endpoint
- Set up Next.js project scaffold in `frontend/` with TypeScript and Tailwind CSS configured

**Done when:**
- `npm install` succeeds at the root (workspaces resolve)
- `npx prisma generate` succeeds in `backend/`
- `types/index.ts` exports Task, User, and ApiResponse interfaces
- `backend/src/middleware/auth.ts` exports a working auth middleware function
- TypeScript compilation passes for `types/` and `backend/` packages

### Parallel Units (Phase 2)

| # | Unit Name | Files (create/modify) | Description | E2E Test |
|---|-----------|----------------------|-------------|----------|
| 1 | Backend Task Routes | Create: `backend/src/routes/tasks.ts` | CRUD endpoints for tasks (GET, POST, PUT, DELETE /tasks) protected by auth middleware. Imports types from `types/` and uses Prisma client for DB operations. | `curl` against each task endpoint with a valid JWT returns correct responses; unauthorized requests return 401 |
| 2 | Backend Auth Routes | Create: `backend/src/routes/auth.ts` | Register and login endpoints. Hashes passwords, creates users via Prisma, issues JWTs on successful login. Imports types from `types/`. | POST /auth/register creates a user; POST /auth/login with valid credentials returns a JWT |
| 3 | Frontend UI | Create: `frontend/src/lib/api.ts`, Create: `frontend/src/components/TaskList.tsx`, Create: `frontend/src/components/TaskForm.tsx`, Create: `frontend/src/components/AuthForm.tsx` | API client that wraps fetch calls and imports shared types. Three React components: TaskList (list/toggle/delete), TaskForm (create/edit), AuthForm (login/register). | `next build` succeeds with no TypeScript errors; components render without runtime errors |

### Dependency & Conflict Analysis
- **File conflicts:** No file is touched by more than one unit. Foundation owns all shared infrastructure files (types, Prisma schema, auth middleware, scaffolding). Each parallel unit creates its own exclusive files. The two backend route files (`tasks.ts` and `auth.ts`) are in separate units. All four frontend files are grouped in a single unit to avoid splitting the API client from the components that import it.
- **Runtime dependencies:** None between parallel units. Backend task routes and backend auth routes do not import from each other (both independently import from `types/` and use Prisma, which are established in foundation). Frontend components import from `frontend/src/lib/api.ts` which is co-located in the same unit. Frontend communicates with backend via HTTP calls, not code imports, so there is no build-time dependency between the frontend unit and the backend route units.

### Post-Merge Verification
1. Run `npm install` at the monorepo root — all workspaces resolve without errors
2. Run `npx prisma generate` in `backend/` — Prisma client generates successfully
3. Start the backend server — health check endpoint responds at GET /health
4. Register a new user via POST /auth/register — returns success with user data
5. Login via POST /auth/login — returns a valid JWT
6. Use the JWT to create, list, update, and delete tasks via the /tasks endpoints
7. Run `next build` in `frontend/` — builds with zero TypeScript errors
8. Full auth flow end-to-end: register, login, create task, view task list, toggle status, delete task
