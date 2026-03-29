"""Tests for scraper job orchestration."""

from flat_research.db import SearchCriteria
from flat_research.scraper_job import compute_union_criteria


class TestComputeUnionCriteria:
    def _make_criteria(self, **kwargs) -> SearchCriteria:
        c = SearchCriteria()
        c.neighbourhoods = kwargs.get("neighbourhoods", {})
        c.price_min = kwargs.get("price_min", 1000)
        c.price_max = kwargs.get("price_max", 2000)
        c.bedrooms_min = kwargs.get("bedrooms_min", 1)
        c.bedrooms_max = kwargs.get("bedrooms_max", None)
        c.furnished = kwargs.get("furnished", False)
        c.parking = kwargs.get("parking", False)
        return c

    def test_single_user(self):
        criteria = [self._make_criteria(price_min=1500, price_max=2500, bedrooms_min=2)]
        result = compute_union_criteria(criteria)
        assert result["criteria"]["price_min"] == 1500
        assert result["criteria"]["price_max"] == 2500
        assert result["criteria"]["bedrooms_min"] == 2

    def test_two_users_widens_range(self):
        c1 = self._make_criteria(price_min=1000, price_max=1500, bedrooms_min=2)
        c2 = self._make_criteria(price_min=2000, price_max=3000, bedrooms_min=3)
        result = compute_union_criteria([c1, c2])
        assert result["criteria"]["price_min"] == 1000
        assert result["criteria"]["price_max"] == 3000
        assert result["criteria"]["bedrooms_min"] == 2

    def test_merges_neighbourhoods(self):
        c1 = self._make_criteria(neighbourhoods={"Villeray": ["villeray"]})
        c2 = self._make_criteria(neighbourhoods={"Plateau": ["plateau"], "Villeray": ["villeray", "parc-ex"]})
        result = compute_union_criteria([c1, c2])
        hoods = result["criteria"]["neighbourhoods"]
        assert "Villeray" in hoods
        assert "Plateau" in hoods
        assert "parc-ex" in hoods["Villeray"]

    def test_furnished_parking_always_false(self):
        """Union criteria always sets furnished/parking to False to get the widest results."""
        c = self._make_criteria(furnished=True, parking=True)
        result = compute_union_criteria([c])
        assert result["criteria"]["furnished"] is False
        assert result["criteria"]["parking"] is False
