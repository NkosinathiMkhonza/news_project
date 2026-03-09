News Application Design Assets

This folder contains supporting design material for the Django news project.
The files here are supplementary documentation for review and submission.

Included assets

- `use_case_diagram.png`: high-level interactions for readers, journalists, editors, and administrators
- `sequence_diagram.png`: article workflow sequence from creation through review and publication
- `class_diagram.png`: core data model relationships
- `MVC_architecture_diagram.png`: application structure overview
- `CRUD_Matrix.txt`: implementation-aligned permission summary

Implemented roles

- `Reader`: reads published articles, comments on published articles, and manages subscriptions
- `Journalist`: creates articles, edits own draft or rejected articles, and submits them for review
- `Editor`: creates publishers, reviews pending articles, and can edit, approve, reject, or delete articles
- `Admin`: full access through Django admin

Notes

- There is no separate in-app `Publisher` user role in the current implementation.
- The project includes a `Newsletter` model in the admin, but there is no dedicated publisher-facing newsletter workflow in the public UI.
- The REST API currently exposes:
  - `/api/articles/`
  - `/api/articles/<id>/`
  - `/api/categories/`
  - `/api/publishers/`
  - `/api/comments/`
  - `/api/subscriptions/`
