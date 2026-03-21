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
