import onnxruntime as ort
import numpy as np

session = ort.InferenceSession("/Users/umangsharma/Desktop/med-auth/facial-recognition/models/MobileFaceNet.onnx")
print("Inputs:", [i.name for i in session.get_inputs()])
print("Outputs:", [o.name for o in session.get_outputs()])
dummy_input = np.random.rand(1, 3, 112, 112).astype(np.float32)
output = session.run(None, {"input0": dummy_input})
print("Output shape:", np.array(output[0]).shape)
