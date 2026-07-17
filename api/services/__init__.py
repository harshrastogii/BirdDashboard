"""Services: application use-cases.

They orchestrate repositories + the birddash core, enforce authorization,
translate between domain data and API DTOs, and own pagination. Routers stay
thin; the core stays framework-free.
"""
