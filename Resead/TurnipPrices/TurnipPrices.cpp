#include "TurnipPrices.h"

// munged from https://github.com/simontime/Resead

#pragma warning(disable : 4305) // disable truncation warnings

using namespace std;

#define TEST_MODE 0

namespace SEAD
{
 
    void Random::init()
    {
        init(42069);
    }

    void Random::init(uint32_t seed)
    {
        mContext[0] = 0x6C078965 * (seed ^ (seed >> 30)) + 1;
        mContext[1] = 0x6C078965 * (mContext[0] ^ (mContext[0] >> 30)) + 2;
        mContext[2] = 0x6C078965 * (mContext[1] ^ (mContext[1] >> 30)) + 3;
        mContext[3] = 0x6C078965 * (mContext[2] ^ (mContext[2] >> 30)) + 4;
    }

    void Random::init(uint32_t seed1, uint32_t seed2, uint32_t seed3, uint32_t seed4)
    {
        if ((seed1 | seed2 | seed3 | seed4) == 0) // seeds must not be all zero.
        {
            seed1 = 1;
            seed2 = 0x6C078967;
            seed3 = 0x714ACB41;
            seed4 = 0x48077044;
        }

        mContext[0] = seed1;
        mContext[1] = seed2;
        mContext[2] = seed3;
        mContext[3] = seed4;
    }

    uint32_t Random::getU32()
    {
        uint32_t n = mContext[0] ^ (mContext[0] << 11);

        mContext[0] = mContext[1];
        mContext[1] = mContext[2];
        mContext[2] = mContext[3];
        mContext[3] = n ^ (n >> 8) ^ mContext[3] ^ (mContext[3] >> 19);

        return mContext[3];
    }

    uint64_t Random::getU64()
    {
        uint32_t n1 = mContext[0] ^ (mContext[0] << 11);
        uint32_t n2 = mContext[1];
        uint32_t n3 = n1 ^ (n1 >> 8) ^ mContext[3];

        mContext[0] = mContext[2];
        mContext[1] = mContext[3];
        mContext[2] = n3 ^ (mContext[3] >> 19);
        mContext[3] = n2 ^ (n2 << 11) ^ ((n2 ^ (n2 << 11)) >> 8) ^ mContext[2] ^ (n3 >> 19);

        return ((uint64_t)mContext[2] << 32) | mContext[3];
    }

    void Random::getContext(uint32_t* seed1, uint32_t* seed2, uint32_t* seed3, uint32_t* seed4) const
    {
        *seed1 = mContext[0];
        *seed2 = mContext[1];
        *seed3 = mContext[2];
        *seed4 = mContext[3];
    }
} // namespace SEAD



namespace PREDICT
{

	/************************************************************************/
	/* Pattern Generation Functions                                         */
	/************************************************************************/

    bool TurnipPrices::DecreasingPhase(const GivenPrices& prices, PriceRangeArray& predictedPrices, int32_t minRate, int32_t maxRate, const int32_t minRateDelta, const int32_t maxRateDelta, const int32_t startIndex, const int32_t endIndex)
    {

		for (int32_t index = startIndex; index < endIndex; index++)
		{

			int32_t minPred = int32_t(floor(float_t(minRate * prices.daisyMaePrice) / 10000.0f));
			int32_t maxPred = int32_t(ceil(float_t(maxRate * prices.daisyMaePrice) / 10000.0f));


			if (prices.IsPriceSet(index))
			{

				if (IsOutsidePredictedRange(prices, index, minPred, maxPred))
				{
					// Given price is out of predicted range, so this is the wrong pattern
					return false;
				}

				const int32_t price = prices[index];
				minPred = price;
				maxPred = price;
				minRate = MinimumRateFromGivenAndBase(price, prices.daisyMaePrice);
				maxRate = MaximumRateFromGivenAndBase(price, prices.daisyMaePrice);
			}

			predictedPrices[index - 2].min = minPred;
			predictedPrices[index - 2].max = maxPred;

			minRate -= minRateDelta;
			maxRate -= maxRateDelta;

		}

        return true;
    }

    bool TurnipPrices::IncreasingPhase(const GivenPrices& prices, PriceRangeArray& predictedPrices, const int32_t startIndex, const int32_t endIndex)
    {
        for (int32_t index = startIndex; index < endIndex; index++)
        {
            const float_t lowFactor = 0.9f, highFactor = 1.4f;
            int32_t minPred = int32_t(floor(lowFactor * float_t(prices.daisyMaePrice)));
            int32_t maxPred = int32_t(ceil(highFactor * float_t(prices.daisyMaePrice)));

            if (prices.IsPriceSet(index))
            {

                if (IsOutsidePredictedRange(prices, index, minPred, maxPred))
                {
                    // Given price is out of predicted range, so this is the wrong pattern
                    return false;
                }

				const int32_t price = prices[index];
				minPred = price;
				maxPred = price;
            }

			predictedPrices[index - 2].min = minPred;
			predictedPrices[index - 2].max = maxPred;

        }

        return true;
		
    }

	void TurnipPrices::GeneratePattern0WithLengths(const GivenPrices& prices, PossibilitiesList& possList, int32_t highPhase1Len, int32_t decPhase1Len, int32_t highPhase2Len, int32_t decPhase2Len, int32_t highPhase3Len)
	{
        // PATTERN 0: high, decreasing, high, decreasing, high
        
        PriceRangeArray predictedPrices;
        
        // High Phase 1
        int32_t minIndex = 2, maxIndex = 2 + highPhase1Len;

        if (!IncreasingPhase(prices, predictedPrices, minIndex, maxIndex))
        {
			// Given price is out of predicted range, so this is the wrong pattern
			return;
        }
        minIndex = maxIndex;
        maxIndex += decPhase1Len;

        // Dec Phase 1
        if (!DecreasingPhase(prices, predictedPrices, 6000, 8000, 1000, 400, minIndex, maxIndex))
        {
			// Given price is out of predicted range, so this is the wrong pattern
			return;
        }
        minIndex = maxIndex;
        maxIndex += highPhase2Len;

        // High Phase 2
        if (!IncreasingPhase(prices, predictedPrices, minIndex, maxIndex))
        {
			// Given price is out of predicted range, so this is the wrong pattern
			return;
        }
        minIndex = maxIndex;
        maxIndex += decPhase2Len;

        // Dec Phase 2
        if (!DecreasingPhase(prices, predictedPrices, 6000, 8000, 1000, 400, minIndex, maxIndex))
        {
			// Given price is out of predicted range, so this is the wrong pattern
			return;
        }
        minIndex = maxIndex;
        maxIndex = GivenPrices::GP_ARR_SIZE;

        // High Phase 3
        if (!IncreasingPhase(prices, predictedPrices, minIndex, maxIndex))
        {
			// Given price is out of predicted range, so this is the wrong pattern
			return;
        }

		// Considered a valid possible pattern, add to the list
		possList.push_back(Poss(predictedPrices, PP_HDHDH));
	}

	void TurnipPrices::GeneratePattern0(const GivenPrices& prices, PossibilitiesList& possList)
	{
        
        // PATTERN 0: high, decreasing, high, decreasing, high
        for (int32_t decPhase1Len = 2; decPhase1Len < 4; ++decPhase1Len)
        {
            for (int32_t highPhase1Len = 0; highPhase1Len < 7; ++highPhase1Len)
            {
                const int32_t highPhase3LenMax = 7 - highPhase1Len; // -1 + 1 in js??
                for (int32_t highPhase3Len = 0; highPhase3Len < highPhase3LenMax; ++highPhase3Len)
                {
                    GeneratePattern0WithLengths(prices, possList, highPhase1Len, decPhase1Len, 7 - highPhase1Len - highPhase3Len, 5 - decPhase1Len, highPhase3Len);
                }
            }
        }
	}

	void TurnipPrices::GeneratePattern1WithPeak(const GivenPrices& prices, PossibilitiesList& possList, int32_t peakStart)
	{

        PriceRangeArray predictedPrices;

        
        // PATTERN 1: decreasing middle, high spike, random low
        int32_t minRate = 8500, maxRate = 9000;

        if (!DecreasingPhase(prices, predictedPrices, 8500, 9000, 500, 300, 2, peakStart))
        {
            // Pattern doesn't match   
            return;
        }
		

        // Now each day is independent of next
        const float_t minRandoms[] = { 0.9f, 1.4f, 2.0f, 1.4f, 0.9f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f, 0.4f };
        const float_t maxRandoms[] = { 1.4f, 2.0f, 6.0f, 2.0f, 1.4f, 0.9f, 0.9f, 0.9f, 0.9f, 0.9f, 0.9f };

        for (int32_t index = peakStart; index < GivenPrices::GP_ARR_SIZE; index++)
        {
			int32_t minPred = int32_t(floor(minRandoms[index - peakStart] * float_t(prices.daisyMaePrice)));
			int32_t maxPred = int32_t(ceil(maxRandoms[index - peakStart] * float_t(prices.daisyMaePrice)));

            if (prices.IsPriceSet(index))
            {
                if (IsOutsidePredictedRange(prices, index, minPred, maxPred))
                {
                    // Given price is out of predicted range, so this is the wrong pattern
                    return;
                }

				const int32_t price = prices[index];
				minPred = price;
				maxPred = price;
            }

			predictedPrices[index - 2].min = minPred;
			predictedPrices[index - 2].max = maxPred;

        }

        // Considered a valid possible pattern, add to the list
        possList.push_back(Poss(predictedPrices, PP_DMHSRL));

	}

	void TurnipPrices::GeneratePattern1(const GivenPrices& prices, PossibilitiesList& possList)
	{
        // PATTERN 1: decreasing middle, high spike, random low
		for (int32_t peakStart = 3; peakStart < 10; ++peakStart)
		{
			GeneratePattern1WithPeak(prices, possList, peakStart);
		}

	}

	void TurnipPrices::GeneratePattern2(const GivenPrices& prices, PossibilitiesList& possList)
	{
        // PATTERN 2: consistently decreasing
        PriceRangeArray predictedPrices;

        if (!DecreasingPhase(prices, predictedPrices, 8500, 9000, 500, 300, 2, GivenPrices::GP_ARR_SIZE))
        {
			// Pattern doesn't match   
			return;
        }

		// Considered a valid possible pattern, add to the list
		possList.push_back(Poss(predictedPrices, PP_CD));
	}

    void TurnipPrices::GeneratePattern3WithPeak(const GivenPrices& prices, PossibilitiesList& possList, int32_t peakStart)
    {
        // PATTERN 3: decreasing, spike, decreasing
        PriceRangeArray predictedPrices;

		if (!DecreasingPhase(prices, predictedPrices, 4000, 9000, 500, 300, 2, peakStart))
		{
			// Pattern doesn't match   
			return;
		}

        // The peak

		if (!IncreasingPhase(prices, predictedPrices, peakStart, peakStart+2))
		{
			// Given price is out of predicted range, so this is the wrong pattern
			return;
		}


        // #TODO this could be made more accurate, I've not bothered with forward/backward calculating of the rate each side of the peak value
		for (int32_t index = peakStart+2; index < peakStart+5; index++)
		{
			const float_t lowFactor = 1.4f, highFactor = 2.0f;
			int32_t minPred = int32_t(floor(lowFactor * float_t(prices.daisyMaePrice)));
			int32_t maxPred = int32_t(ceil(highFactor * float_t(prices.daisyMaePrice)));

            if (index != peakStart + 3)
            {
                minPred -= 1;
                maxPred -= 1;
            }

			if (prices.IsPriceSet(index))
			{

				if (IsOutsidePredictedRange(prices, index, minPred, maxPred))
				{
					// Given price is out of predicted range, so this is the wrong pattern
					return;
				}

				const int32_t price = prices[index];
				minPred = price;
				maxPred = price;
			}

			predictedPrices[index - 2].min = minPred;
			predictedPrices[index - 2].max = maxPred;

		}


        // Optional last phase decrease
		if (!DecreasingPhase(prices, predictedPrices, 4000, 9000, 500, 300, peakStart+5, GivenPrices::GP_ARR_SIZE))
		{
			// Pattern doesn't match   
			return;
		}

		// Considered a valid possible pattern, add to the list
		possList.push_back(Poss(predictedPrices, PP_DSD));
    }

	void TurnipPrices::GeneratePattern3(const GivenPrices& prices, PossibilitiesList& possList)
	{
        // PATTERN 3: decreasing, spike, decreasing
        for (int32_t peakStart = 3; peakStart < 10; ++peakStart)
		{
			GeneratePattern3WithPeak(prices, possList, peakStart);
		}
	}

    
    uint32_t TurnipPrices::CalculatePossibilities(const GivenPrices& prices, PossibilitiesList& possList)
    {
        possList.clear();

        if (prices.HasDaisyMaePriceBeenSet())
        {
            GeneratePattern0(prices, possList);
            GeneratePattern1(prices, possList);
            GeneratePattern2(prices, possList);
            GeneratePattern3(prices, possList);
        }
        else
        {
            GivenPrices gp = prices;
            for (int32_t buyPrice = 90; buyPrice <= 110; ++buyPrice)
            {
                gp.daisyMaePrice = buyPrice;
                GeneratePattern0(gp, possList);
				GeneratePattern1(prices, possList);
				GeneratePattern2(prices, possList);
				GeneratePattern3(prices, possList);
            }
        }
        

		return uint32_t(possList.size());
	}


  //  void TurnipPrices::calculate()
  //  {
		//int32_t basePrice;
		//int32_t sellPrices[14];
		//uint32_t whatPattern;
		//int32_t tmp40;
  //      
  //      basePrice = randint(90, 110);
  //      int chance = randint(0, 99);

  //      // select the next pattern
  //      int nextPattern;

  //      for (int i = 2; i < 14; i++)
  //          sellPrices[i] = 0;
  //      sellPrices[0] = basePrice;
  //      sellPrices[1] = basePrice;

  //      int work;
  //      int decPhaseLen1, decPhaseLen2, peakStart;
  //      int hiPhaseLen1, hiPhaseLen2and3, hiPhaseLen3;
  //      float rate;

  //      switch (whatPattern)
  //      {
  //      case 0:
  //          // PATTERN 0: high, decreasing, high, decreasing, high
  //          work = 2;
  //          decPhaseLen1 = randbool() ? 3 : 2;
  //          decPhaseLen2 = 5 - decPhaseLen1;

  //          hiPhaseLen1 = randint(0, 6);
  //          hiPhaseLen2and3 = 7 - hiPhaseLen1;
  //          hiPhaseLen3 = randint(0, hiPhaseLen2and3 - 1);

  //          // high phase 1
  //          for (int i = 0; i < hiPhaseLen1; i++)
  //          {
  //              sellPrices[work++] = intceil(randfloat(0.9, 1.4) * basePrice);
  //          }

  //          // decreasing phase 1
  //          rate = randfloat(0.8, 0.6);
  //          for (int i = 0; i < decPhaseLen1; i++)
  //          {
  //              sellPrices[work++] = intceil(rate * basePrice);
  //              rate -= 0.04;
  //              rate -= randfloat(0, 0.06);
  //          }

  //          // high phase 2
  //          for (int i = 0; i < (hiPhaseLen2and3 - hiPhaseLen3); i++)
  //          {
  //              sellPrices[work++] = intceil(randfloat(0.9, 1.4) * basePrice);
  //          }

  //          // decreasing phase 2
  //          rate = randfloat(0.8, 0.6);
  //          for (int i = 0; i < decPhaseLen2; i++)
  //          {
  //              sellPrices[work++] = intceil(rate * basePrice);
  //              rate -= 0.04;
  //              rate -= randfloat(0, 0.06);
  //          }

  //          // high phase 3
  //          for (int i = 0; i < hiPhaseLen3; i++)
  //          {
  //              sellPrices[work++] = intceil(randfloat(0.9, 1.4) * basePrice);
  //          }
  //          break;
  //      case 1:
  //          // PATTERN 1: decreasing middle, high spike, random low
  //          peakStart = randint(3, 9);
  //          rate = randfloat(0.9, 0.85);
  //          for (work = 2; work < peakStart; work++)
  //          {
  //              sellPrices[work] = intceil(rate * basePrice);
  //              rate -= 0.03;
  //              rate -= randfloat(0, 0.02);
  //          }
  //          sellPrices[work++] = intceil(randfloat(0.9, 1.4) * basePrice);
  //          sellPrices[work++] = intceil(randfloat(1.4, 2.0) * basePrice);
  //          sellPrices[work++] = intceil(randfloat(2.0, 6.0) * basePrice);
  //          sellPrices[work++] = intceil(randfloat(1.4, 2.0) * basePrice);
  //          sellPrices[work++] = intceil(randfloat(0.9, 1.4) * basePrice);
  //          for (; work < 14; work++)
  //          {
  //              sellPrices[work] = intceil(randfloat(0.4, 0.9) * basePrice);
  //          }
  //          break;
  //      case 2:
  //          // PATTERN 2: consistently decreasing
  //          rate = 0.9;
  //          rate -= randfloat(0, 0.05);
  //          for (work = 2; work < 14; work++)
  //          {
  //              sellPrices[work] = intceil(rate * basePrice);
  //              rate -= 0.03;
  //              rate -= randfloat(0, 0.02);
  //          }
  //          break;
  //      case 3:
  //          // PATTERN 3: decreasing, spike, decreasing
  //          peakStart = randint(2, 9);

  //          // decreasing phase before the peak
  //          rate = randfloat(0.9, 0.4);
  //          for (work = 2; work < peakStart; work++)
  //          {
  //              sellPrices[work] = intceil(rate * basePrice);
  //              rate -= 0.03;
  //              rate -= randfloat(0, 0.02);
  //          }

  //          sellPrices[work++] = intceil(randfloat(0.9, 1.4) * (float)basePrice);
  //          sellPrices[work++] = intceil(randfloat(0.9, 1.4) * basePrice);
  //          rate = randfloat(1.4, 2.0);
  //          sellPrices[work++] = intceil(randfloat(1.4, rate) * basePrice) - 1;
  //          sellPrices[work++] = intceil(rate * basePrice);
  //          sellPrices[work++] = intceil(randfloat(1.4, rate) * basePrice) - 1;

  //          // decreasing phase after the peak
  //          if (work < 14)
  //          {
  //              rate = randfloat(0.9, 0.4);
  //              for (; work < 14; work++)
  //              {
  //                  sellPrices[work] = intceil(rate * basePrice);
  //                  rate -= 0.03;
  //                  rate -= randfloat(0, 0.02);
  //              }
  //          }
  //          break;
  //      }

  //      sellPrices[0] = 0;
  //      sellPrices[1] = 0;
  //  }
} // namespace PREDICT

int main(int argc, char** argv)
{
    using namespace PREDICT;
    
    TurnipPrices turnips;

    PossibilitiesList pbl;

#if TEST_MODE
    if(true)
    {

        char* debugArgs[] = { "exepath", "test.csv", "100", "97", "122", "106", "117", "80", "71", "0", "0", "0", "0", "0", "0" };
#else
	if (argc == GivenPrices::GP_ARR_SIZE + 1)
	{
#endif


        
         // First get given prices from command line args
        const int32_t gpArraySize = GivenPrices::GP_ARR_SIZE;
        int32_t gpArray[gpArraySize];


        cout << "gpArray: ";
        for (int32_t i = 0; i < gpArraySize; ++i)
        {
            
#if TEST_MODE
            if (i >= 2)
            {
                gpArray[i] = int32_t(atoi(debugArgs[i+1]));
            }
            else
            {
                gpArray[i] = int32_t(atoi(debugArgs[2]));
            }
#else
			if (i >= 2)
			{
				gpArray[i] = int32_t(atoi(argv[i+1]));
			}
			else
			{
				gpArray[i] = int32_t(atoi(argv[2]));
			}
#endif

            cout << ' ' << to_string(gpArray[i]);

        }

        cout << endl;

        GivenPrices gp(gpArray);

        // Calculate the possible patterns and prices
        const uint32_t numPossibilities = turnips.CalculatePossibilities(gp, pbl);

        // Output calculations to a CSV file
        ofstream csvFile;
#if TEST_MODE
        csvFile.open("test.csv");
#else
        csvFile.open(argv[1]);
#endif


        cout << "TurnipPrices: With given prices there are " << to_string(numPossibilities) << " possible patterns." << endl;
        for (Poss poss : pbl)
        {

            csvFile << int32_t(poss.pattern) << ",";
            for (uint32_t i = 0; i < PRA_ARR_SIZE; ++i)
            {
                csvFile << poss.priceArray[i].min << ',' << poss.priceArray[i].max << ',';
            }
            csvFile << endl;

            printf("Sun  Mon  Tue  Wed  Thu  Fri  Sat\n");

            printf("%3d  %3d  %3d  %3d  %3d  %3d  %3d\n",
                gp.daisyMaePrice,
                poss.priceArray[0].max, poss.priceArray[2].max, poss.priceArray[4].max,
                poss.priceArray[6].max, poss.priceArray[8].max, poss.priceArray[10].max);
            printf("%3d  %3d  %3d  %3d  %3d  %3d  %3d\n",
                gp.daisyMaePrice,
                poss.priceArray[0].min, poss.priceArray[2].min, poss.priceArray[4].min,
                poss.priceArray[6].min, poss.priceArray[8].min, poss.priceArray[10].min);

            printf("\n");
            printf("     %3d  %3d  %3d  %3d  %3d  %3d\n",
                poss.priceArray[1].max, poss.priceArray[3].max, poss.priceArray[5].max,
                poss.priceArray[7].max, poss.priceArray[9].max, poss.priceArray[11].max);
            printf("     %3d  %3d  %3d  %3d  %3d  %3d\n",
                poss.priceArray[1].min, poss.priceArray[3].min, poss.priceArray[5].min,
                poss.priceArray[7].min, poss.priceArray[9].min, poss.priceArray[11].min);
            printf("\n\n");

        }
    }
    else
    {
        cout << "Incorrect number of arguments: " << to_string(argc) << " Need csv path, buy price, then 12 entry prices" << endl;
    }

    return 0;
}