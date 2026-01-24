from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.db import models
import json
import os
import glob


def model_label(m):
    return f"{m._meta.app_label}.{m._meta.model_name}"


class Command(BaseCommand):
    help = "Validate that all FK/M2M references in fixtures resolve to existing objects."

    def add_arguments(self, parser):
        parser.add_argument("--src", default="app/backend/fixtures")

    def handle(self, *args, **opts):
        src = opts["src"]
        files = sorted(glob.glob(os.path.join(src, "*.json")))
        if not files:
            raise CommandError(f"No JSON fixtures found in {src}")

        uuid_pk_by_model = {
            model_label(m): isinstance(m._meta.pk, models.UUIDField) for m in apps.get_models()
        }
        model_by_label = {model_label(m): m for m in apps.get_models()}

        objects = []  # list of tuples (path, obj)
        present = set()  # (model_label, pk)
        for path in files:
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception as e:
                    raise CommandError(f"Invalid JSON in {path}: {e}") from e
                for obj in data:
                    objects.append((path, obj))
                    present.add((obj.get("model"), obj.get("pk")))

        errors = []
        for path, obj in objects:
            ml = obj.get("model")
            fields = obj.get("fields", {})
            m = model_by_label.get(ml)
            if not m:
                continue

            for f in m._meta.get_fields():
                if f.many_to_one and f.concrete and f.name in fields:
                    target_ml = model_label(f.remote_field.model)
                    val = fields[f.name]
                    if val is None:
                        continue
                    # Check only if target model has UUID PK (i.e., was converted)
                    if uuid_pk_by_model.get(target_ml) and (target_ml, val) not in present:
                        errors.append(
                            f"Missing FK target {target_ml}:{val} referenced from {ml}.{f.name} in {path}"
                        )

                if f.many_to_many and f.name in fields:
                    target_ml = model_label(f.remote_field.model)
                    if uuid_pk_by_model.get(target_ml):
                        for v in fields[f.name]:
                            if (target_ml, v) not in present:
                                errors.append(
                                    f"Missing M2M target {target_ml}:{v} referenced from {ml}.{f.name} in {path}"
                                )

        if errors:
            for e in errors:
                self.stderr.write(e)
            raise CommandError(f"{len(errors)} reference errors found.")
        self.stdout.write(self.style.SUCCESS("Fixture references validated."))
