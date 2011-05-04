#include "config.h"
#include "fftw3.h"
#include "ltfat.h"

LTFAT_EXTERN
void LTFAT_NAME(dgt_fac)(const LTFAT_COMPLEX *f, const LTFAT_COMPLEX *gf,
			 const int L, const int W, const int a,
			 const int M, LTFAT_COMPLEX *cout)
{

   const int N=L/a;
   
  /* Create plan. In-place. */
   LTFAT_FFTW(plan) p_veryend = 
     LTFAT_FFTW(plan_many_dft)(1, &M, N*W,
			       cout, NULL,
			       1, M,
			       cout, NULL,
			       1, M,
			       FFTW_FORWARD, FFTW_ESTIMATE);

   LTFAT_NAME(dgt_walnut)(f,gf,L,W,a,M,cout);
      
   /* FFT to modulate the coefficients. */
   LTFAT_FFTW(execute)(p_veryend);   

   LTFAT_FFTW(destroy_plan)(p_veryend);   
}

LTFAT_NAME(ltfat_plan)
LTFAT_NAME(plan_dgt_long)(const LTFAT_COMPLEX *f, const LTFAT_COMPLEX *g,
			  const int L, const int W,
			  const int a, const int M, LTFAT_COMPLEX *cout,
			  unsigned flags)		      
{

   LTFAT_NAME(ltfat_plan) plan;
   int h_m;

   plan.a=a;
   plan.M=M;
   plan.L=L;
   plan.W=W;
   const int N=L/a;
   const int b=L/M;

   plan.c=gcd(a, M,&plan.h_a, &h_m);
   const int p=a/plan.c;
   plan.d=b/p;
   plan.h_a=-plan.h_a;

   plan.sbuf = (LTFAT_REAL*)ltfat_malloc(2*plan.d*sizeof(LTFAT_REAL));
   plan.cout = cout;
   plan.f    = f;

   plan.gf   = (LTFAT_COMPLEX*)ltfat_malloc(L*sizeof(LTFAT_COMPLEX));

   /* Get factorization of window */
   LTFAT_NAME(wfac)(g, L, a, M, plan.gf);
   
  /* Create plans. In-place. */
   plan.p_veryend = 
      LTFAT_FFTW(plan_many_dft)(1, &M, N*W,
				plan.cout, NULL,
				1, M,
				plan.cout, NULL,
				1, M,
				FFTW_FORWARD, flags);
   
   plan.p_before = 
      LTFAT_FFTW(plan_dft_1d)(plan.d, (LTFAT_COMPLEX*)plan.sbuf,
			      (LTFAT_COMPLEX*)plan.sbuf,
			      FFTW_FORWARD, flags);
   
   plan.p_after  = 
      LTFAT_FFTW(plan_dft_1d)(plan.d, (LTFAT_COMPLEX*)plan.sbuf,
			      (LTFAT_COMPLEX*)plan.sbuf,
			      FFTW_BACKWARD, flags);         
   
   return plan;
}

LTFAT_NAME(ltfat_plan_real)
LTFAT_NAME(plan_dgtreal_long)(const LTFAT_COMPLEX *f, const LTFAT_COMPLEX *g,
			  const int L, const int W,
			  const int a, const int M, LTFAT_COMPLEX *cout,
			  unsigned flags)		      
{

   LTFAT_NAME(ltfat_plan_real) plan;
   int h_m;

   plan.a=a;
   plan.M=M;
   plan.L=L;
   plan.W=W;
   const int N=L/a;
   const int b=L/M;

   plan.c=gcd(a, M,&plan.h_a, &h_m);
   const int p=a/plan.c;
   plan.d=b/p;
   plan.h_a=-plan.h_a;

   const int M2=M/2+1;
   const int d2=d/2+1;

   plan.sbuf = ltfat_malloc(plan.d*sizeof(LTFAT_REAL));
   plan.cbuf = ltfat_malloc(    d2*sizeof(LTFAT_COMPLEX));
   plan.cout = cout;
   plan.f    = f;

   const int wfs = wfacreal_size(L,a,M);

   plan.gf   = (LTFAT_COMPLEX*)ltfat_malloc(wfs*sizeof(LTFAT_COMPLEX));

   /* Get factorization of window */
   LTFAT_NAME(wfacreal)(g, L, a, M, plan.gf);
   
  /* Create plans. In-place. */
   plan.p_veryend = 
      LTFAT_FFTW(plan_many_dft_r2c)(1, &plan.M, N*W,
                                  cwork, NULL,
                                  1, M,
                                  cout, NULL,
				  1, M2,
				  flags);

   plan.p_before = 
      LTFAT_FFTW(plan_dft_r2c_1d)(plan.d, plan.sbuf,
			      plan.cbuf, flags);
   
   plan.p_after  = 
      LTFAT_FFTW(plan_dft_c2r_1d)(plan.d, plan.cbuf,
			      plan.sbuf, flags);         
   
   return plan;
}



void LTFAT_NAME(ltfat_execute_plan)(const LTFAT_NAME(ltfat_plan) plan)
{

   LTFAT_NAME(dgt_walnut_plan)(plan,plan.f,(const LTFAT_COMPLEX*)plan.gf);
      
   /* FFT to modulate the coefficients. */
   LTFAT_FFTW(execute)(plan.p_veryend);   

}


void LTFAT_NAME(ltfat_destroy_plan)(LTFAT_NAME(ltfat_plan) plan)
{

   LTFAT_FFTW(destroy_plan)(plan.p_veryend);
   LTFAT_FFTW(destroy_plan)(plan.p_before);
   LTFAT_FFTW(destroy_plan)(plan.p_after);

   ltfat_free(plan.sbuf);
   ltfat_free(plan.gf);
}

void LTFAT_NAME(ltfat_destroy_plan_real)(LTFAT_NAME(ltfat_plan_real) plan)
{

   LTFAT_FFTW(destroy_plan)(plan.p_veryend);
   LTFAT_FFTW(destroy_plan)(plan.p_before);
   LTFAT_FFTW(destroy_plan)(plan.p_after);

   ltfat_free(plan.sbuf);
   ltfat_free(plan.cbuf);
   ltfat_free(plan.gf);
}



/* -------------- Real valued signal ------------------------ */

LTFAT_EXTERN
void LTFAT_NAME(dgt_fac_r)(const LTFAT_REAL *f, const LTFAT_COMPLEX *gf,
			   const int L,
			   const int W, const int a,
			   const int M, LTFAT_COMPLEX *cout)
{

   const int N=L/a;
   
   /* Create plan. In-place. */
   LTFAT_FFTW(plan) p_veryend = 
     LTFAT_FFTW(plan_many_dft)(1, &M, N*W,
			       cout, NULL,
			       1, M,
			       cout, NULL,
			       1, M,
			       FFTW_FORWARD, FFTW_ESTIMATE);
   
   LTFAT_NAME(dgt_walnut_r)(f,gf,L,W,a,M,cout);
      
   /* FFT to modulate the coefficients. */
   LTFAT_FFTW(execute)(p_veryend);   

   LTFAT_FFTW(destroy_plan)(p_veryend);   
   
}
