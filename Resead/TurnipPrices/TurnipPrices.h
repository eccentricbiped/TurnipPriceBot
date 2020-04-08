// Header file for the TurnipPrices project

#pragma once

#include <vector>
#include <iostream>
#include <fstream>


namespace SEAD
{
	class Random
	{
	public:
		void init();
		void init(uint32_t seed);
		void init(uint32_t seed1, uint32_t seed2, uint32_t seed3, uint32_t seed4);
		uint32_t getU32();
		uint64_t getU64();
		void getContext(uint32_t* seed1, uint32_t* seed2, uint32_t* seed3, uint32_t* seed4) const;

	private:
		uint32_t mContext[4];
	};
}

uint32_t pf(float f) {
	return *((uint32_t*)&f);
}

namespace PREDICT
{
	struct PriceRange
	{
		PriceRange() : min(0), max(0) {}
		PriceRange(int32_t p) : min(p), max(p) {}
		PriceRange(int32_t min_p, int32_t max_p) : min(min_p), max(max_p) {}
		int32_t min, max;
	};


	static const uint32_t PRA_ARR_SIZE = 12;
	typedef PriceRange PriceRangeArray[PRA_ARR_SIZE];

	enum PricePattern
	{
		PP_NONE = -1,	// Default, unset value
		PP_HDHDH = 0,	// high, decreasing, high, decreasing, high
		PP_DMHSRL = 1,	// decreasing middle, high spike, random low
		PP_CD = 2,		// constantly decreasing
		PP_DSD = 3		// decreasing, spike, decreasing
	};

	struct Poss
	{
		Poss() : pattern(PP_NONE) {}
		Poss(PriceRangeArray pra, PricePattern pp) : pattern(pp) 
		{
			memcpy(&priceArray[0], &pra[0], PRA_ARR_SIZE * sizeof(PriceRange));
		}
		
		PriceRangeArray priceArray;
		PricePattern pattern;
	};

	typedef std::vector<Poss> PossibilitiesList;

	struct GivenPrices
	{
		static const uint8_t GP_ARR_SIZE = 14;
		GivenPrices() {}
		GivenPrices(int32_t pa[]) 
		{
			memcpy(&nookPrices[0], &pa[0], GP_ARR_SIZE * sizeof(int32_t));
		}

		bool HasDaisyMaePriceBeenSet() const { return daisyMaePrice > 0;  }

		bool IsPriceSet(int32_t i) const { return nookPrices[i] > 0; }

		// Syntactic Sugar indexing into nookPrices
		int32_t operator [](int32_t i) const { return nookPrices[i]; }
		int32_t& operator [](int32_t i) { return nookPrices[i]; }


		// Given price data
		int32_t nookPrices[GP_ARR_SIZE] = { 0 };
		int32_t& daisyMaePrice = nookPrices[0];
	};



	class TurnipPrices
	{


	public:

		//void calculate();
		uint32_t CalculatePossibilities(const GivenPrices& prices, PossibilitiesList& possList);
	
	private:

		/************************************************************************/
		/* Pattern Generation Functions                                         */
		/************************************************************************/
	
		void GeneratePattern0(const GivenPrices& prices, PossibilitiesList& possList);
		void GeneratePattern0WithLengths(const GivenPrices& prices, PossibilitiesList& possList, int32_t highPhase1Len, int32_t decPhase1Len, int32_t highPhase2Len, int32_t decPhase2Len, int32_t highPhase3Len);
		
		void GeneratePattern1(const GivenPrices& prices, PossibilitiesList& possList);
		void GeneratePattern1WithPeak(const GivenPrices& prices, PossibilitiesList& possList, int32_t peakStart);
		
		void GeneratePattern2(const GivenPrices& prices, PossibilitiesList& possList);
		
		void GeneratePattern3(const GivenPrices& prices, PossibilitiesList& possList);
		void GeneratePattern3WithPeak(const GivenPrices& prices, PossibilitiesList& possList, int32_t peakStart);

		

	private:

		bool DecreasingPhase(const GivenPrices& prices, PriceRangeArray& predictedPrices, int32_t minRate, int32_t maxRate, const int32_t minRateDelta, const int32_t maxRateDelta, const int32_t startIndex, const int32_t endIndex);
		bool IncreasingPhase(const GivenPrices& prices, PriceRangeArray& predictedPrices, const int32_t startIndex, const int32_t endIndex);
		
		
		// utility stuff for testing
		SEAD::Random rng;
		bool randbool()
		{
			return rng.getU32() & 0x80000000;
		}
		int randint(int min, int max)
		{
			return (((uint64_t)rng.getU32() * (uint64_t)(max - min + 1)) >> 32) + min;
		}
		float randfloat(float a, float b)
		{
			uint32_t val = 0x3F800000 | (rng.getU32() >> 9);
			float fval = *(float*)(&val);
			return a + ((fval - 1.0f) * (b - a));
		}
		int intceil(float val)
		{
			return (int)(val + 0.99999f);
		}

		/************************************************************************/
		/* Internal Helper Functions                                            */
		/************************************************************************/


		void AppendPriceRangeArray(PriceRangeArray& dest, const PriceRangeArray& source)
		{
			//dest.insert(source.end(), source.begin(), source.end());
		}

		int32_t MinimumRateFromGivenAndBase(int32_t givenPrice, int32_t buyPrice) const
		{
			return 10000 * (givenPrice - 1) / buyPrice;
		}

		int32_t MaximumRateFromGivenAndBase(int32_t givenPrice, int32_t buyPrice) const
		{
			return 10000 * givenPrice / buyPrice;
		}
		
		bool IsOutsidePredictedRange(const GivenPrices& prices, int32_t index, int32_t minPredict, int32_t maxPredict) const
		{
			bool result = true;
			
			if (index >= 0 && index < GivenPrices::GP_ARR_SIZE)
			{
				result = prices.nookPrices[index] < minPredict || prices.nookPrices[index] > maxPredict;
			}

			return result;
			
		}

	};

} // namespace PREDICT


