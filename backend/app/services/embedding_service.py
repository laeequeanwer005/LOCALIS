from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F


# =========================================================
# LOCAL EMBEDDING MODEL
# =========================================================

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_tokenizer = None
_model = None


# =========================================================
# LOAD MODEL
# =========================================================

def get_embedding_model():

    global _tokenizer
    global _model

    if (
        _tokenizer is None
        or _model is None
    ):

        print("=" * 70)
        print("Loading LOCALIS embedding model...")
        print("Model:", MODEL_NAME)
        print("=" * 70)

        _tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME
        )

        _model = AutoModel.from_pretrained(
            MODEL_NAME
        )

        _model.eval()

        # CPU optimization
        if not torch.cuda.is_available():

            try:

                torch.set_num_threads(
                    max(
                        1,
                        min(
                            8,
                            torch.get_num_threads()
                        )
                    )
                )

            except Exception:
                pass

        print(
            "LOCALIS embedding model loaded."
        )

        print("=" * 70)

    return _tokenizer, _model


# =========================================================
# MEAN POOLING
# =========================================================

def mean_pooling(
    model_output,
    attention_mask
):

    token_embeddings = (
        model_output.last_hidden_state
    )

    input_mask_expanded = (
        attention_mask
        .unsqueeze(-1)
        .expand(
            token_embeddings.size()
        )
        .float()
    )

    return torch.sum(
        token_embeddings
        * input_mask_expanded,
        dim=1
    ) / torch.clamp(
        input_mask_expanded.sum(
            dim=1
        ),
        min=1e-9
    )


# =========================================================
# CREATE EMBEDDINGS
# =========================================================

def create_embeddings(
    texts: list[str]
) -> list[list[float]]:

    if not texts:

        return []

    tokenizer, model = (
        get_embedding_model()
    )

    encoded_input = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=256,
        return_tensors="pt"
    )

    with torch.inference_mode():

        model_output = model(
            **encoded_input
        )

    embeddings = mean_pooling(
        model_output,
        encoded_input[
            "attention_mask"
        ]
    )

    embeddings = F.normalize(
        embeddings,
        p=2,
        dim=1
    )

    return embeddings.cpu().tolist()


# =========================================================
# CREATE SINGLE EMBEDDING
# =========================================================

def create_embedding(
    text: str
) -> list[float]:

    embeddings = create_embeddings(
        [text]
    )

    if not embeddings:

        return []

    return embeddings[0]


# =========================================================
# COSINE SIMILARITY
# =========================================================

def cosine_similarity(
    embedding_a: list[float],
    embedding_b: list[float]
) -> float:

    if not embedding_a or not embedding_b:

        return 0.0

    a = torch.tensor(
        embedding_a,
        dtype=torch.float32
    )

    b = torch.tensor(
        embedding_b,
        dtype=torch.float32
    )

    a = F.normalize(
        a,
        p=2,
        dim=0
    )

    b = F.normalize(
        b,
        p=2,
        dim=0
    )

    return float(
        torch.dot(
            a,
            b
        )
    )