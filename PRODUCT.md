# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are job-seeking professionals managing resumes, applications,
interviews, and career development. This is inferred from the implemented
routes and backend models and should be confirmed with product stakeholders.

## Product Purpose

CV Agent brings the job-search workflow into one workspace: CV editing and ATS
analysis, job matching, interview preparation, application tracking, LinkedIn
optimization, salary analysis, and career roadmaps. Success means helping a
user see the next best action and move their search forward with less
fragmentation. This statement is inferred from the current product surface.

## Positioning

The product combines AI-assisted career preparation and active job-search
operations in a single workspace rather than treating each task as a separate
tool. This positioning is inferred and remains open for confirmation.

## Operating Context

Users work with CV files, job descriptions, application stages, interview
dates, profile data, and career goals. The interface is used repeatedly during
an active job search, so clarity and fast navigation are durable requirements.

## Capabilities and Constraints

- Next.js 16 and React 19 frontend with a FastAPI backend.
- Authenticated application shell with public login and registration routes.
- Existing API contracts, routes, terminology, and working interactions must
  remain intact during the redesign.
- Turkish is the primary language currently visible in the interface.

## Brand Commitments

- Product name: CV Agent.
- The user explicitly requested an exceptionally bold, memorable visual result.
- The interface must still feel credible enough for sensitive career data.

## Evidence on Hand

The repository contains working UI routes, API clients, domain models, tests,
and sample uploaded CV documents. There are no confirmed customer claims,
testimonials, benchmark figures, or commercial metrics; future design work must
not fabricate them.

## Product Principles

- Make the next career action obvious.
- Let AI guidance support user judgment rather than obscure it.
- Keep dense career information calm, scannable, and actionable.
- Preserve trust while giving the product a distinctive point of view.
- Treat accessibility and responsive behavior as part of product quality.

## Accessibility & Inclusion

Meet WCAG AA contrast, preserve keyboard navigation and visible focus, respect
reduced-motion preferences, and keep touch targets at least 44×44 px.
