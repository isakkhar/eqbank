from django.core.management.base import BaseCommand
from core.models import Question

class Command(BaseCommand):
    help = "Normalize question_type values to canonical keys: mcq, short, creative"

    MAPPING = {
        'mcq': ['mcq', 'multiple', 'multiple choice', 'multiple-choice', 'multiplechoice', 'বহু', 'বহুনির্বাচনী', 'বহু-নির্বাচনী', 'বহু নির্বাচনি', 'multiple choice', 'multiple choice '],
        'short': ['short', 'সংক্ষিপ্ত', 'সংক্ষেপ', 'short answer', 'short-answer'],
        'creative': ['creative', 'সৃজন', 'সৃজনশীল'],
    }

    def normalize(self, val):
        if not val:
            return ''
        v = val.strip().lower()
        for key, variants in self.MAPPING.items():
            for variant in variants:
                if variant in v:
                    return key
        return v  # fallback: leave lowercased original (will require manual review)

    def handle(self, *args, **options):
        total = 0
        changed = 0
        for q in Question.objects.all():
            total += 1
            old = (q.question_type or '').strip()
            new = self.normalize(old)
            if new and new != old:
                q.question_type = new
                q.save(update_fields=['question_type'])
                changed += 1
        self.stdout.write(self.style.SUCCESS(f"Processed {total} questions, updated {changed}."))