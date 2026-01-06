import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';
import { getTrending } from '../api/client';
import type { TimeRange, TrendingResponse } from '../types';

/**
 * Query key factory for trending data
 * Ensures consistent query key structure across the app
 */
export const trendingKeys = {
  all: ['trending'] as const,
  byTimeRange: (timeRange: TimeRange) => ['trending', timeRange] as const,
};

/**
 * Hook for fetching trending ticker data by time range
 *
 * @param timeRange - The time period to fetch data for (24h, 7d, 30d)
 * @returns Query result with trending data, loading state, and error
 *
 * @example
 * const { data, isLoading, error } = useTrendingData('7d');
 */
export function useTrendingData(
  timeRange: TimeRange
): UseQueryResult<TrendingResponse, Error> {
  return useQuery({
    queryKey: trendingKeys.byTimeRange(timeRange),
    queryFn: () => getTrending(timeRange),
  });
}
