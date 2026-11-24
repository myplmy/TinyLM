/* Existing five-trit payload only: no master matrix, file I/O or retained pointers. */
#include <stdint.h>
#include <stddef.h>
#include <limits.h>
#define D(b,p) (((b)/(p))%3-1)
#define ROW(b) {D(b,1),D(b,3),D(b,9),D(b,27),D(b,81)}
static const int8_t DIGITS[243][5] = {
    ROW(0), ROW(1), ROW(2), ROW(3), ROW(4), ROW(5), ROW(6), ROW(7), ROW(8), ROW(9), ROW(10), ROW(11),
    ROW(12), ROW(13), ROW(14), ROW(15), ROW(16), ROW(17), ROW(18), ROW(19), ROW(20), ROW(21), ROW(22), ROW(23),
    ROW(24), ROW(25), ROW(26), ROW(27), ROW(28), ROW(29), ROW(30), ROW(31), ROW(32), ROW(33), ROW(34), ROW(35),
    ROW(36), ROW(37), ROW(38), ROW(39), ROW(40), ROW(41), ROW(42), ROW(43), ROW(44), ROW(45), ROW(46), ROW(47),
    ROW(48), ROW(49), ROW(50), ROW(51), ROW(52), ROW(53), ROW(54), ROW(55), ROW(56), ROW(57), ROW(58), ROW(59),
    ROW(60), ROW(61), ROW(62), ROW(63), ROW(64), ROW(65), ROW(66), ROW(67), ROW(68), ROW(69), ROW(70), ROW(71),
    ROW(72), ROW(73), ROW(74), ROW(75), ROW(76), ROW(77), ROW(78), ROW(79), ROW(80), ROW(81), ROW(82), ROW(83),
    ROW(84), ROW(85), ROW(86), ROW(87), ROW(88), ROW(89), ROW(90), ROW(91), ROW(92), ROW(93), ROW(94), ROW(95),
    ROW(96), ROW(97), ROW(98), ROW(99), ROW(100), ROW(101), ROW(102), ROW(103), ROW(104), ROW(105), ROW(106), ROW(107),
    ROW(108), ROW(109), ROW(110), ROW(111), ROW(112), ROW(113), ROW(114), ROW(115), ROW(116), ROW(117), ROW(118), ROW(119),
    ROW(120), ROW(121), ROW(122), ROW(123), ROW(124), ROW(125), ROW(126), ROW(127), ROW(128), ROW(129), ROW(130), ROW(131),
    ROW(132), ROW(133), ROW(134), ROW(135), ROW(136), ROW(137), ROW(138), ROW(139), ROW(140), ROW(141), ROW(142), ROW(143),
    ROW(144), ROW(145), ROW(146), ROW(147), ROW(148), ROW(149), ROW(150), ROW(151), ROW(152), ROW(153), ROW(154), ROW(155),
    ROW(156), ROW(157), ROW(158), ROW(159), ROW(160), ROW(161), ROW(162), ROW(163), ROW(164), ROW(165), ROW(166), ROW(167),
    ROW(168), ROW(169), ROW(170), ROW(171), ROW(172), ROW(173), ROW(174), ROW(175), ROW(176), ROW(177), ROW(178), ROW(179),
    ROW(180), ROW(181), ROW(182), ROW(183), ROW(184), ROW(185), ROW(186), ROW(187), ROW(188), ROW(189), ROW(190), ROW(191),
    ROW(192), ROW(193), ROW(194), ROW(195), ROW(196), ROW(197), ROW(198), ROW(199), ROW(200), ROW(201), ROW(202), ROW(203),
    ROW(204), ROW(205), ROW(206), ROW(207), ROW(208), ROW(209), ROW(210), ROW(211), ROW(212), ROW(213), ROW(214), ROW(215),
    ROW(216), ROW(217), ROW(218), ROW(219), ROW(220), ROW(221), ROW(222), ROW(223), ROW(224), ROW(225), ROW(226), ROW(227),
    ROW(228), ROW(229), ROW(230), ROW(231), ROW(232), ROW(233), ROW(234), ROW(235), ROW(236), ROW(237), ROW(238), ROW(239),
    ROW(240), ROW(241), ROW(242)
};
#undef ROW
#undef D

uint32_t p014e_cpu_abi(void) { return UINT32_C(0x50453036); }

static int valid_shape(int64_t m,int64_t n,int64_t k,int64_t g) {
    return m>0 && m<=1024 && n>0 && n<=(INT64_C(1)<<24)
        && k>0 && k<=(INT64_C(1)<<20) && g>0 && g<=k && k%g==0
        && m<=INT64_MAX/n;
}

int p014e_cpu_linear(const float *x,const uint8_t *codes,const float *scales,float *y,
                     int64_t m,int64_t n,int64_t k,int64_t g,int64_t begin,int64_t end) {
    if(!x || !codes || !scales || !y || !valid_shape(m,n,k,g)
       || begin<0 || end<begin || end>m*n) return 1;
    const int64_t groups=k/g,bytes=(g+4)/5;
    for(int64_t flat=begin;flat<end;++flat) {
        const int64_t sample=flat/n,row=flat%n;
        const float *input=x+sample*k;
        double sum=0.0;
        for(int64_t group=0;group<groups;++group) {
            const float scale=scales[row*groups+group];
            const uint8_t *packed=codes+(row*groups+group)*bytes;
            for(int64_t offset=0;offset<g;offset+=5) {
                const uint8_t byte=packed[offset/5];
                if(byte>242) return 4;
                const int8_t *trits=DIGITS[byte];
                for(int j=0;j<5 && offset+j<g;++j) {
                    const float weight=(float)trits[j]*scale;
                    sum+=(double)input[group*g+offset+j]*(double)weight;
                }
            }
        }
        y[flat]=(float)sum;
    }
    return 0;
}

int p014e_cpu_lookup(const uint8_t *codes,const float *scales,const int64_t *ids,float *y,
                     int64_t count,int64_t n,int64_t k,int64_t g) {
    if(!codes || !scales || !ids || !y || !valid_shape(count,n,k,g)) return 1;
    for(int64_t i=0;i<count;++i) if(ids[i]<0 || ids[i]>=n) return 2;
    const int64_t groups=k/g,bytes=(g+4)/5;
    for(int64_t i=0;i<count;++i) {
        const int64_t row=ids[i];
        for(int64_t group=0;group<groups;++group) {
            const float scale=scales[row*groups+group];
            const uint8_t *packed=codes+(row*groups+group)*bytes;
            for(int64_t offset=0;offset<g;offset+=5) {
                const uint8_t byte=packed[offset/5];
                if(byte>242) return 4;
                for(int j=0;j<5 && offset+j<g;++j)
                    y[i*k+group*g+offset+j]=(float)DIGITS[byte][j]*scale;
            }
        }
    }
    return 0;
}
