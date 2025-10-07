print("[INFO] Using stubbed nemo_text_processing (pynini disabled).")

class Normalizer:
    def __init__(self, *args, **kwargs):
        pass

    def normalize(self, text, **kwargs):
        return text
