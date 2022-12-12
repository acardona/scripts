#include <stdio.h>
#include <stdlib.h>


int addIfPrime(int a, int next, int *primes) {
	// Compute the reminder of the division of a by all primes found so far.
	// Start from the second prime, because all numbers can be divided by 1! So j=1.
  for (int j=1; j<next; j++) {
	  //printf("a: %i, next: %i, primes[%i]: %i\n", a, next, j, primes[j]);
    // If the remainder of the division by a prime is not 0, it's not prime.
    if (0 == (a % primes[j])) return 0;
  }
	//printf("  found %i\n", a);
  primes[next] = a;
	return 1;
}

int main(int argc, char *argv[]) {
	if (2 != argc) {
		printf("Please give the maximum number of primes to find as argument, like:\n./find_primes 100\n\n");
		return 0;
	}

  int max = atoi(argv[1]); // if invalid, atoi returns 0

  if (max <= 0) {
		printf("Invalid argument: %s\n", argv[1]);
		return 0;
	}

  int primes[max];
  int next = 0;
  primes[next++] = 1;
  primes[next++] = 2;
  primes[next++] = 3;
  int k = 6;

  while (next < max) {
    next += addIfPrime(k-1, next, primes);
		if (next == max) break;
    next += addIfPrime(k+1, next, primes);
    k += 6;
  }

  for (int j=0; j<next; ++j) {
    printf("%i\n", primes[j]);
  }

	return 1;
}
