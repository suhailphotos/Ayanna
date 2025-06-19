#import insightface
#insightface.model_zoo.get_model('buffalo_l')

from insightface.app import FaceAnalysis

app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0)  # ctx_id=0 means use GPU, -1 means CPU

print("InsightFace model loaded and ready.")
