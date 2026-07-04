from app.core.config import DEFAULT_MODEL


class ModelService:
    """
    Provides information about language models supported by BRAG.

    During Phase 3 BRAG supports a single OpenAI model.

    Future phases will extend this service to expose multiple
    providers and dynamically available models.
    """

    def get_models(self) -> dict:
        """
        Retrieve the currently supported language models.

        Returns:
            Dictionary containing the default model and all
            available models.
        """

        return {
            "default_model": DEFAULT_MODEL,
            "available_models": [
                DEFAULT_MODEL,
            ],
        }


