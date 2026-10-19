import logging
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)


class LocalVisionService:
    _instance = None
    _model = None
    _processor = None
    _load_failed = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self) -> bool:
        """Memuat model BLIP secara lazy (hanya saat dibutuhkan)."""
        if self._model is not None:
            return True
        if self._load_failed:
            return False

        try:
            from transformers import BlipForConditionalGeneration, BlipProcessor

            model_id = "Salesforce/blip-image-captioning-base"
            logger.info(f"Memuat model vision open-source: {model_id}...")

            self._processor = BlipProcessor.from_pretrained(model_id)
            self._model = BlipForConditionalGeneration.from_pretrained(model_id)
            return True
        except Exception as exc:
            logger.warning(f"Gagal memuat local vision model: {exc}")
            self._load_failed = True
            return False

    def describe_image(self, image: Image.Image) -> Optional[str]:
        """Menghasilkan deskripsi visual gambar menggunakan model AI lokal."""
        if not self._load_model():
            return None

        try:
            import re

            # 1. Pastikan gambar dalam format RGB
            rgb_img = image.convert("RGB")

            # 2. Pancingan prompt (Conditional Captioning resmi dari Salesforce BLIP)
            prompt = "a photography of"
            inputs = self._processor(rgb_img, text=prompt, return_tensors="pt")

            # 3. Generate dengan beam search lebih luas dan penalty seimbang
            out = self._model.generate(
                **inputs,
                num_beams=5,
                repetition_penalty=1.35,
                no_repeat_ngram_size=2,
                early_stopping=True,
                max_new_tokens=60,
            )
            caption = self._processor.decode(out[0], skip_special_tokens=True)

            # 4. Bersihkan jika ada kata kembar berturut-turut (misal: 'lamb lamb' -> 'lamb')
            cleaned_caption = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', caption, flags=re.IGNORECASE)

            return cleaned_caption.strip() if cleaned_caption else None
        except Exception as exc:
            logger.error(f"Error saat inferensi visual: {exc}")
            return None