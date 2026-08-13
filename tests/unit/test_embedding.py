import numpy as np

from app.retrieval.embedding import embed


def test_embedding_shape_and_norm():
    vectors = embed(["def draw() {background(220);}","fix typo in readme"])
    assert vectors.shape ==(2,384)
    assert np.allclose(np.linalg.norm(vectors,axis=1),1.0,atol=1e-5)

