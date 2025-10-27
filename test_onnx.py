import onnxruntime as ort
import numpy as np

# Load model
session = ort.InferenceSession("/Users/umangsharma/Desktop/med-auth/facial-recognition/models/MobileFaceNet.onnx")

# Check input/output names
print("Inputs:", [i.name for i in session.get_inputs()])
print("Outputs:", [o.name for o in session.get_outputs()])

# Dummy input (same shape as training: 1x3x112x112)
dummy_input = np.random.rand(1, 3, 112, 112).astype(np.float32)

# Run inference
output = session.run(None, {"input0": dummy_input})
print("Output shape:", np.array(output[0]).shape)
