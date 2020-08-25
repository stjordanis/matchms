from typing import List
import numba
import numpy
from matchms.similarity import SequentialSimilarityFunction
from matchms.similarity import ParallelSimilarityFunction
from matchms.typing import SpectrumType


class ParentmassMatch(SequentialSimilarityFunction, ParallelSimilarityFunction):
    """Return True if spectrums match in parent mass (within tolerance), and False otherwise."""
    # Set key characteristics as class attributes
    is_commutative = True

    def __init__(self, tolerance: float = 0.1):
        """
        Parameters
        ----------
        tolerance
            Specify tolerance below which two masses are counted as match.
        """
        self.tolerance = tolerance

    def compute_scores(self, reference: SpectrumType, query: SpectrumType) -> float:
        """Compare parent masses between reference and query spectrum.

        Parameters
        ----------
        reference
            Single reference spectrum.
        query
            Single query spectrum.
        """
        parentmass_ref = reference.get("parent_mass")
        parentmass_query = query.get("parent_mass")
        assert parentmass_ref is not None and parentmass_query is not None, "Missing parent mass."

        return abs(parentmass_ref - parentmass_query) <= self.tolerance

    def compute_scores_parallel(self, reference: List[SpectrumType], query: List[SpectrumType],
                                is_symmetric: bool = False) -> numpy.ndarray:
        """Compare parent masses between all reference_spectrums and spectrums.

        Parameters
        ----------
        reference
            List/array of reference spectrums.
        query
            List/array of Single query spectrums.
        is_symmetric
            Set to True when *references* and *queries* are identical (as for instance for an all-vs-all
            comparison). By using the fact that score[i,j] = score[j,i] the calculation will be about
            2x faster.
        """
        def collect_parentmasses(spectrums):
            """Collect parentmasses."""
            parentmasses = []
            for spectrum in spectrums:
                parentmass = spectrum.get("parent_mass")
                assert parentmass is not None, "Missing parent mass."
                parentmasses.append(parentmass)
            return numpy.asarray(parentmasses)

        parentmasses_ref = collect_parentmasses(reference)
        parentmasses_query = collect_parentmasses(query)
        if is_symmetric:
            return parentmass_scores_symmetric(parentmasses_ref, parentmasses_query, self.tolerance).astype(bool)
        return parentmass_scores(parentmasses_ref, parentmasses_query, self.tolerance).astype(bool)


@numba.njit
def parentmass_scores(parentmasses_ref, parentmasses_query, tolerance):
    scores = numpy.zeros((len(parentmasses_ref), len(parentmasses_query)))
    for i, parentmass_ref in enumerate(parentmasses_ref):
        for j, parentmass_query in enumerate(parentmasses_query):
            scores[i, j] = (abs(parentmass_ref - parentmass_query) <= tolerance)
    return scores


@numba.njit
def parentmass_scores_symmetric(parentmasses_ref, parentmasses_query, tolerance):
    scores = numpy.zeros((len(parentmasses_ref), len(parentmasses_query)))
    for i, parentmass_ref in enumerate(parentmasses_ref):
        for j, parentmass_query in enumerate(parentmasses_query[i:], start=i):
            scores[i, j] = (abs(parentmass_ref - parentmass_query) <= tolerance)
            scores[j, i] = scores[i, j]
    return scores
