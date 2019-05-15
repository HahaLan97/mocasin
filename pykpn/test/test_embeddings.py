from pykpn.representations.embeddings import *
import pykpn.representations.metric_spaces as metric
from pykpn.representations.examples import *

np.set_printoptions(threshold=np.nan)


distortion = 1.05
M = exampleClusterArch 
E = MetricSpaceEmbeddingBase(M)
print(E.approx(np.random.random(E.k)))
d=5
Evec = MetricSpaceEmbedding(M,d)
print(Evec.i([1,0,1,1,3]))
print(Evec.inv(Evec.i([1,0,1,1,3])))
#print(Evec.invapprox(list(np.random.random((d,E.k))))) # this is failing!

Par = MetricSpaceEmbedding(exampleClusterArch,d,distortion=1.5)
#print(Par.invapprox(list(10*np.random.random((d,Par.k)))))

D = np.matrix([[ 0.,  2.,  2.,  4.,  2.,  4.,  4.,  4.,  4.,  4.,  4.,  4.,  2.,  4.,  2.,  2.,  4.,  2., 4.,  2.],
               [ 2.,  0.,  4.,  2.,  2.,  4.,  4.,  4.,  2.,  4.,  2.,  4.,  4.,  4.,  4.,  2.,  4.,  2., 2.,  4.],
               [ 2.,  4.,  0.,  4.,  4.,  2.,  2.,  4.,  4.,  4.,  4.,  4.,  2.,  4.,  2.,  4.,  2.,  4., 2.,  2.],
               [ 4.,  2.,  4.,  0.,  4.,  4.,  4.,  4.,  2.,  2.,  1.,  4.,  4.,  2.,  2.,  4.,  4.,  4., 2.,  4.],
               [ 2.,  2.,  4.,  4.,  0.,  4.,  2.,  4.,  4.,  4.,  4.,  2.,  4.,  2.,  4.,  2.,  2.,  2., 4.,  4.],
               [ 4.,  4.,  2.,  4.,  4.,  0.,  2.,  2.,  4.,  2.,  4.,  4.,  4.,  4.,  4.,  2.,  2.,  2., 2.,  4.],
               [ 4.,  4.,  2.,  4.,  2.,  2.,  0.,  4.,  4.,  4.,  4.,  2.,  4.,  2.,  4.,  4.,  1.,  4., 2.,  4.],
               [ 4.,  4.,  4.,  4.,  4.,  2.,  4.,  0.,  2.,  2.,  4.,  2.,  2.,  4.,  4.,  2.,  4.,  2., 4.,  2.],
               [ 4.,  2.,  4.,  2.,  4.,  4.,  4.,  2.,  0.,  4.,  2.,  2.,  2.,  4.,  4.,  4.,  4.,  4., 2.,  2.],
               [ 4.,  4.,  4.,  2.,  4.,  2.,  4.,  2.,  4.,  0.,  2.,  4.,  4.,  2.,  2.,  2.,  4.,  2., 4.,  4.],
               [ 4.,  2.,  4.,  1.,  4.,  4.,  4.,  4.,  2.,  2.,  0.,  4.,  4.,  2.,  2.,  4.,  4.,  4., 2.,  4.],
               [ 4.,  4.,  4.,  4.,  2.,  4.,  2.,  2.,  2.,  4.,  4.,  0.,  2.,  2.,  4.,  4.,  2.,  4., 4.,  2.],
               [ 2.,  4.,  2.,  4.,  4.,  4.,  4.,  2.,  2.,  4.,  4.,  2.,  0.,  4.,  2.,  4.,  4.,  4., 4.,  1.],
               [ 4.,  4.,  4.,  2.,  2.,  4.,  2.,  4.,  4.,  2.,  2.,  2.,  4.,  0.,  2.,  4.,  2.,  4., 4.,  4.],
               [ 2.,  4.,  2.,  2.,  4.,  4.,  4.,  4.,  4.,  2.,  2.,  4.,  2.,  2.,  0.,  4.,  4.,  4., 4.,  2.],
               [ 2.,  2.,  4.,  4.,  2.,  2.,  4.,  2.,  4.,  2.,  4.,  4.,  4.,  4.,  4.,  0.,  4.,  1., 4.,  4.],
               [ 4.,  4.,  2.,  4.,  2.,  2.,  1.,  4.,  4.,  4.,  4.,  2.,  4.,  2.,  4.,  4.,  0.,  4., 2.,  4.],
               [ 2.,  2.,  4.,  4.,  2.,  2.,  4.,  2.,  4.,  2.,  4.,  4.,  4.,  4.,  4.,  1.,  4.,  0., 4.,  4.],
               [ 4.,  2.,  2.,  2.,  4.,  2.,  2.,  4.,  2.,  4.,  2.,  4.,  4.,  4.,  4.,  4.,  2.,  4., 0.,  4.],
               [ 2.,  4.,  2.,  4.,  4.,  4.,  4.,  2.,  2.,  4.,  4.,  2.,  1.,  4.,  2.,  4.,  4.,  4., 4.,  0.]])

L = np.matrix(MetricSpaceEmbeddingBase.calculateEmbeddingMatrix(D,distortion))
vecs = L.A
dists = []
for i,v in enumerate(vecs):
    for j,w in enumerate(vecs):
        if D[i,j] != 0:
            dists.append(np.linalg.norm(v-w)/D[i,j])

print(vecs)
print(np.mean(dists))


print(L)
