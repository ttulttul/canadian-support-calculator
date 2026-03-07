import { useEffect, useEffectEvent, useRef, useState } from 'react'
import './App.css'

const defaultScenario = {
  jurisdiction: 'BC',
  children: '2',
  childrenUnderSix: '0',
  taxYear: '2023',
  payorIncome: '244658',
  recipientIncome: '30600',
  targetMinPercent: '40',
  targetMaxPercent: '46',
}

const baseTaxYear = 2023
const defaultExtrapolationRate = 0.025
const combinedApproxTaxBrackets2023 = [
  [0, 45654, 20.06],
  [45654, 53359, 22.7],
  [53359, 91310, 28.2],
  [91310, 104835, 31.0],
  [104835, 106717, 32.79],
  [106717, 127299, 38.29],
  [127299, 165430, 40.7],
  [165430, 172602, 44.02],
  [172602, 235675, 46.12],
  [235675, 240716, 49.8],
  [240716, Number.POSITIVE_INFINITY, 53.5],
]
const knownTaxYearIndexFactors = {
  2017: 45916 / 53359,
  2018: 46605 / 53359,
  2019: 47630 / 53359,
  2020: 48535 / 53359,
  2021: 49020 / 53359,
  2022: 50197 / 53359,
  2023: 1,
  2024: 55867 / 53359,
  2025: 57375 / 53359,
}
const ccbChildCountCap = 4
const ccbConfigs = {
  2021: {
    under6: 6997,
    age6To17: 5903,
    threshold1: 32797,
    threshold2: 71060,
    step1Rates: { 1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23 },
    step2Bases: { 1: 2678, 2: 5166, 3: 7270, 4: 8801 },
    step2Rates: { 1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095 },
  },
  2022: {
    under6: 7437,
    age6To17: 6275,
    threshold1: 34863,
    threshold2: 75537,
    step1Rates: { 1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23 },
    step2Bases: { 1: 2847, 2: 5490, 3: 7726, 4: 9352 },
    step2Rates: { 1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095 },
  },
  2023: {
    under6: 7787,
    age6To17: 6570,
    threshold1: 36502,
    threshold2: 79087,
    step1Rates: { 1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23 },
    step2Bases: { 1: 2981, 2: 5749, 3: 8091, 4: 9795 },
    step2Rates: { 1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095 },
  },
  2024: {
    under6: 7997,
    age6To17: 6748,
    threshold1: 37487,
    threshold2: 81222,
    step1Rates: { 1: 0.07, 2: 0.135, 3: 0.19, 4: 0.23 },
    step2Bases: { 1: 3061, 2: 5904, 3: 8310, 4: 10059 },
    step2Rates: { 1: 0.032, 2: 0.057, 3: 0.08, 4: 0.095 },
  },
}
const gstConfigs = {
  2021: {
    baseCredit: 306,
    childCredit: 161,
    singleSupplement: 161,
    singleSupplementThreshold: 9919,
    phaseoutThreshold: 39826,
  },
  2022: {
    baseCredit: 325,
    childCredit: 171,
    singleSupplement: 171,
    singleSupplementThreshold: 10544,
    phaseoutThreshold: 42335,
  },
  2023: {
    baseCredit: 340,
    childCredit: 179,
    singleSupplement: 179,
    singleSupplementThreshold: 11039,
    phaseoutThreshold: 44324,
  },
  2024: {
    baseCredit: 349,
    childCredit: 184,
    singleSupplement: 184,
    singleSupplementThreshold: 11337,
    phaseoutThreshold: 45521,
  },
}
const bcFamilyBenefitConfigs = {
  2022: {
    maxFirstChild: 1750,
    maxSecondChild: 1100,
    maxAdditionalChild: 900,
    minFirstChild: 775,
    minSecondChild: 750,
    minAdditionalChild: 725,
    maxThreshold: 27354,
    phaseoutThreshold: 87533,
    singleParentSupplement: 500,
  },
  2023: {
    maxFirstChild: 2188,
    maxSecondChild: 1375,
    maxAdditionalChild: 1125,
    minFirstChild: 969,
    minSecondChild: 937,
    minAdditionalChild: 906,
    maxThreshold: 35902,
    phaseoutThreshold: 114887,
    singleParentSupplement: 500,
  },
  2024: {
    maxFirstChild: 1750,
    maxSecondChild: 1100,
    maxAdditionalChild: 900,
    minFirstChild: 775,
    minSecondChild: 750,
    minAdditionalChild: 725,
    maxThreshold: 29526,
    phaseoutThreshold: 94483,
    singleParentSupplement: 500,
  },
}
const bcClimateConfigs = {
  2021: {
    adult: 447,
    secondAdultOrFirstChild: 223.5,
    additionalChild: 111.5,
    singleThreshold: 39115,
    familyThreshold: 50170,
  },
  2022: {
    adult: 504,
    secondAdultOrFirstChild: 252,
    additionalChild: 126,
    singleThreshold: 41071,
    familyThreshold: 57288,
  },
  2023: {
    adult: 504,
    secondAdultOrFirstChild: 252,
    additionalChild: 126,
    singleThreshold: 41071,
    familyThreshold: 57288,
  },
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'CAD',
    maximumFractionDigits: 0,
  }).format(value ?? 0)
}

function formatPercent(value) {
  return `${Number(value ?? 0).toFixed(2)}%`
}

function formatSignedCurrency(value) {
  if (value > 0) {
    return `+${formatCurrency(value)}`
  }
  if (value < 0) {
    return `-${formatCurrency(Math.abs(value))}`
  }
  return formatCurrency(0)
}

function asNumber(value, fallback = 0) {
  return Number.isFinite(Number(value)) ? Number(value) : fallback
}

function resolveTaxYearIndexFactor(taxYear) {
  if (taxYear in knownTaxYearIndexFactors) {
    return knownTaxYearIndexFactors[taxYear]
  }

  const knownYears = Object.keys(knownTaxYearIndexFactors).map(Number)
  const minYear = Math.min(...knownYears)
  const maxYear = Math.max(...knownYears)

  if (taxYear < minYear) {
    const years = minYear - taxYear
    return knownTaxYearIndexFactors[minYear] / (1 + defaultExtrapolationRate) ** years
  }

  const years = taxYear - maxYear
  return knownTaxYearIndexFactors[maxYear] * (1 + defaultExtrapolationRate) ** years
}

function calculateApproxBcTax(income, taxYear) {
  const normalizedIncome = Math.max(asNumber(income), 0)
  const factor = resolveTaxYearIndexFactor(taxYear)
  let tax = 0

  for (const [lower, upper, rate] of combinedApproxTaxBrackets2023) {
    const indexedLower = lower * factor
    const indexedUpper = upper === Number.POSITIVE_INFINITY ? upper : upper * factor
    if (normalizedIncome <= indexedLower) {
      break
    }

    const taxableAmount = Math.min(normalizedIncome, indexedUpper) - indexedLower
    tax += taxableAmount * rate / 100
  }

  return Number(tax.toFixed(2))
}

function calculateEquivalentBeforeTaxIncome(targetNetIncome, taxYear) {
  const normalizedTarget = Math.max(asNumber(targetNetIncome), 0)
  if (normalizedTarget <= 0) {
    return 0
  }

  let lower = normalizedTarget
  let upper = Math.max(normalizedTarget, 1)

  while (upper - calculateApproxBcTax(upper, taxYear) < normalizedTarget && upper < 10_000_000) {
    upper *= 2
  }

  for (let index = 0; index < 80; index += 1) {
    const midpoint = (lower + upper) / 2
    const derivedNetIncome = midpoint - calculateApproxBcTax(midpoint, taxYear)

    if (derivedNetIncome < normalizedTarget) {
      lower = midpoint
    } else {
      upper = midpoint
    }
  }

  return Number(upper.toFixed(2))
}

function scaleConfig(configs, taxYear) {
  if (taxYear in configs) {
    return configs[taxYear]
  }

  const years = Object.keys(configs).map(Number)
  const sourceYear = taxYear < Math.min(...years) ? Math.min(...years) : Math.max(...years)
  const scale = resolveTaxYearIndexFactor(taxYear) / resolveTaxYearIndexFactor(sourceYear)
  const sourceConfig = configs[sourceYear]

  return Object.fromEntries(
    Object.entries(sourceConfig).map(([key, value]) => {
      if (typeof value === 'object' && value !== null) {
        if (key.endsWith('Rates')) {
          return [key, value]
        }

        return [
          key,
          Object.fromEntries(
            Object.entries(value).map(([nestedKey, nestedValue]) => [
              nestedKey,
              Number((nestedValue * scale).toFixed(2)),
            ]),
          ),
        ]
      }

      return [key, Number((value * scale).toFixed(2))]
    }),
  )
}

function calculateCanadaChildBenefit(income, numChildren, childrenUnderSix, taxYear) {
  if (numChildren <= 0) {
    return 0
  }

  const config = scaleConfig(ccbConfigs, taxYear)
  const cappedCount = Math.min(numChildren, ccbChildCountCap)
  const childrenOverSix = numChildren - childrenUnderSix
  const maximumBenefit = config.under6 * childrenUnderSix + config.age6To17 * childrenOverSix
  let reduction = 0

  if (income > config.threshold2) {
    reduction =
      config.step2Bases[cappedCount] + (income - config.threshold2) * config.step2Rates[cappedCount]
  } else if (income > config.threshold1) {
    reduction = (income - config.threshold1) * config.step1Rates[cappedCount]
  }

  return Number(Math.max(maximumBenefit - reduction, 0).toFixed(2))
}

function calculateGstHstCredit(income, registeredChildren, taxYear) {
  const config = scaleConfig(gstConfigs, taxYear)
  const subtotal =
    registeredChildren > 0
      ? config.baseCredit +
        config.baseCredit +
        config.childCredit * Math.max(registeredChildren - 1, 0) +
        config.singleSupplement
      : config.baseCredit +
        Math.min(
          config.singleSupplement,
          Math.max(income - config.singleSupplementThreshold, 0) * 0.02,
        )

  return Number(
    Math.max(subtotal - Math.max(income - config.phaseoutThreshold, 0) * 0.05, 0).toFixed(2),
  )
}

function calculateBcFamilyBenefitChildAmount(
  count,
  firstChildAmount,
  secondChildAmount,
  additionalChildAmount,
) {
  if (count <= 0) {
    return 0
  }
  if (count === 1) {
    return firstChildAmount
  }
  if (count === 2) {
    return firstChildAmount + secondChildAmount
  }

  return firstChildAmount + secondChildAmount + additionalChildAmount * (count - 2)
}

function calculateBcFamilyBenefit(income, registeredChildren, taxYear) {
  if (registeredChildren <= 0) {
    return 0
  }

  const config = scaleConfig(bcFamilyBenefitConfigs, taxYear)
  const maximumChildAmount = calculateBcFamilyBenefitChildAmount(
    registeredChildren,
    config.maxFirstChild,
    config.maxSecondChild,
    config.maxAdditionalChild,
  )
  const guaranteedMinimum = calculateBcFamilyBenefitChildAmount(
    registeredChildren,
    config.minFirstChild,
    config.minSecondChild,
    config.minAdditionalChild,
  )
  const maximumTotal = maximumChildAmount + config.singleParentSupplement

  if (income <= config.maxThreshold) {
    return Number(maximumTotal.toFixed(2))
  }
  if (income <= config.phaseoutThreshold) {
    return Number(
      Math.max(maximumTotal - (income - config.maxThreshold) * 0.04, guaranteedMinimum).toFixed(2),
    )
  }

  return Number(
    Math.max(guaranteedMinimum - (income - config.phaseoutThreshold) * 0.04, 0).toFixed(2),
  )
}

function calculateBcClimateActionCredit(income, registeredChildren, taxYear) {
  if (taxYear >= 2024) {
    return 0
  }

  const config = scaleConfig(bcClimateConfigs, taxYear)
  const threshold = registeredChildren > 0 ? config.familyThreshold : config.singleThreshold
  const maximumCredit =
    registeredChildren > 0
      ? config.adult +
        config.secondAdultOrFirstChild +
        config.additionalChild * Math.max(registeredChildren - 1, 0)
      : config.adult

  return Number(Math.max(maximumCredit - Math.max(income - threshold, 0) * 0.02, 0).toFixed(2))
}

function calculateSharedCustodyBenefits(payorIncome, recipientIncome, numChildren, childrenUnderSix, taxYear) {
  const multiplier = 0.5
  const buildBreakdown = (income) => {
    const canadaChildBenefitAnnual = calculateCanadaChildBenefit(
      income,
      numChildren,
      childrenUnderSix,
      taxYear,
    )
    const gstHstCreditAnnual = calculateGstHstCredit(income, numChildren, taxYear)
    const bcFamilyBenefitAnnual = calculateBcFamilyBenefit(income, numChildren, taxYear)
    const bcClimateActionCreditAnnual = calculateBcClimateActionCredit(income, numChildren, taxYear)

    return {
      canadaChildBenefitAnnual: Number((canadaChildBenefitAnnual * multiplier).toFixed(2)),
      gstHstCreditAnnual: Number((gstHstCreditAnnual * multiplier).toFixed(2)),
      bcFamilyBenefitAnnual: Number((bcFamilyBenefitAnnual * multiplier).toFixed(2)),
      bcClimateActionCreditAnnual: Number((bcClimateActionCreditAnnual * multiplier).toFixed(2)),
    }
  }

  const payor = buildBreakdown(payorIncome)
  const recipient = buildBreakdown(recipientIncome)

  return {
    payor: {
      ...payor,
      totalAnnual: Number(
        (
          payor.canadaChildBenefitAnnual +
          payor.gstHstCreditAnnual +
          payor.bcFamilyBenefitAnnual +
          payor.bcClimateActionCreditAnnual
        ).toFixed(2),
      ),
    },
    recipient: {
      ...recipient,
      totalAnnual: Number(
        (
          recipient.canadaChildBenefitAnnual +
          recipient.gstHstCreditAnnual +
          recipient.bcFamilyBenefitAnnual +
          recipient.bcClimateActionCreditAnnual
        ).toFixed(2),
      ),
    },
  }
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.error ?? 'Request failed.')
  }

  return data
}

function DetailList({ items, emphasis = false }) {
  return (
    <dl className={`detail-list${emphasis ? ' detail-list--emphasis' : ''}`}>
      {items.map((item) => (
        <div key={item.label} className="detail-list__row">
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

function CurrencyCell({ value, signed = false }) {
  const amount = asNumber(value)
  const className = [
    'currency-cell',
    signed ? 'signed-value' : '',
    signed && amount > 0 ? 'signed-value--positive' : '',
    signed && amount < 0 ? 'signed-value--negative' : '',
  ]
    .filter(Boolean)
    .join(' ')
  const content = signed ? formatSignedCurrency(amount) : formatCurrency(amount)

  return <span className={className}>{content}</span>
}

function ResultTable({ caption, columns, rows, numericColumnIndexes = [] }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <caption>{caption}</caption>
        <thead>
          <tr>
            {columns.map((column, index) => (
              <th
                key={column}
                className={numericColumnIndexes.includes(index) ? 'data-table__numeric' : ''}
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={typeof row[0] === 'object' && row[0] !== null ? row[0].key : row[0]}>
              {row.map((cell, index) => (
                <td
                  key={typeof cell === 'object' && cell !== null ? cell.key : `${row[0]}-${index}`}
                  className={`${numericColumnIndexes.includes(index) ? 'data-table__numeric' : ''} ${
                    typeof cell === 'object' && cell !== null && cell.className ? cell.className : ''
                  }`.trim()}
                >
                  {typeof cell === 'object' && cell !== null ? cell.content : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function App() {
  const [metadata, setMetadata] = useState(null)
  const [scenario, setScenario] = useState(defaultScenario)
  const [autoRecalculate, setAutoRecalculate] = useState(true)
  const [netIncomePeriod, setNetIncomePeriod] = useState('annual')
  const [spousalDetailsOpen, setSpousalDetailsOpen] = useState(false)
  const [childResult, setChildResult] = useState(null)
  const [spousalResult, setSpousalResult] = useState(null)
  const [childError, setChildError] = useState('')
  const [spousalError, setSpousalError] = useState('')
  const [metadataError, setMetadataError] = useState('')
  const [isCalculating, setIsCalculating] = useState(false)
  const requestSequence = useRef(0)

  useEffect(() => {
    let active = true

    async function loadMetadata() {
      const response = await fetch('/api/metadata')
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.error ?? 'Unable to load calculator metadata.')
      }

      if (active) {
        setMetadata(data)
      }
    }

    loadMetadata().catch((error) => {
      if (active) {
        setMetadataError(error.message)
      }
    })

    return () => {
      active = false
    }
  }, [])

  async function submitScenario(activeScenario) {
    const requestId = requestSequence.current + 1
    requestSequence.current = requestId
    setIsCalculating(true)
    setChildError('')
    setSpousalError('')

    const payload = {
      jurisdiction: activeScenario.jurisdiction,
      children: Number(activeScenario.children),
      childrenUnderSix: Number(activeScenario.childrenUnderSix),
      taxYear: Number(activeScenario.taxYear),
      payorIncome: Number(activeScenario.payorIncome),
      recipientIncome: Number(activeScenario.recipientIncome),
    }

    const [childResponse, spousalResponse] = await Promise.allSettled([
      postJson('/api/calculate/child-support', payload),
      postJson('/api/calculate/spousal-support', {
        ...payload,
        targetMinPercent: Number(activeScenario.targetMinPercent),
        targetMaxPercent: Number(activeScenario.targetMaxPercent),
      }),
    ])

    if (requestId !== requestSequence.current) {
      return
    }

    if (childResponse.status === 'fulfilled') {
      setChildResult(childResponse.value)
    } else {
      setChildResult(null)
      setChildError(childResponse.reason.message)
    }

    if (spousalResponse.status === 'fulfilled') {
      setSpousalResult(spousalResponse.value)
    } else {
      setSpousalResult(null)
      setSpousalError(spousalResponse.reason.message)
    }

    setIsCalculating(false)
  }

  const submitCurrentScenario = useEffectEvent((activeScenario) => {
    const requiredFields = [
      activeScenario.children,
      activeScenario.childrenUnderSix,
      activeScenario.taxYear,
      activeScenario.payorIncome,
      activeScenario.recipientIncome,
      activeScenario.targetMinPercent,
      activeScenario.targetMaxPercent,
    ]
    if (requiredFields.some((value) => value === '')) {
      return
    }

    void submitScenario(activeScenario)
  })

  useEffect(() => {
    if (!metadata || !autoRecalculate) {
      return
    }

    submitCurrentScenario(scenario)
  }, [autoRecalculate, metadata, scenario])

  function handleScenarioChange(event) {
    const { name, value } = event.target
    setScenario((current) => {
      if (name === 'children') {
        const nextChildren = value
        const nextChildrenUnderSix = Math.min(
          Number(current.childrenUnderSix || 0),
          Number(nextChildren || 0),
        )
        return {
          ...current,
          children: nextChildren,
          childrenUnderSix: String(nextChildrenUnderSix),
        }
      }

      if (name === 'childrenUnderSix') {
        const boundedValue = Math.min(Number(value || 0), Number(current.children || 0))
        return { ...current, childrenUnderSix: String(Math.max(boundedValue, 0)) }
      }

      return { ...current, [name]: value }
    })
  }

  function handleSubmit(event) {
    event.preventDefault()
    void submitScenario(scenario)
  }

  function handleReset() {
    setScenario(defaultScenario)
  }

  const supportedChildren = metadata?.supportedChildren ?? []
  const childRows = childResult
    ? [
        ['Payor', formatCurrency(childResult.payorMonthly), formatCurrency(childResult.payorAnnual)],
        [
          'Recipient',
          formatCurrency(childResult.recipientMonthly),
          formatCurrency(childResult.recipientAnnual),
        ],
        ['Net transfer', formatCurrency(childResult.netMonthly), formatCurrency(childResult.netAnnual)],
      ]
    : []
  const spousalHistoryRows =
    spousalResult?.history.slice(-6).map((entry) => [
      `#${entry.iteration}`,
      formatCurrency(entry.spousalSupportAnnual),
      formatPercent(entry.recipientSharePercent),
    ]) ?? []
  const payorGrossIncome = spousalResult ? asNumber(spousalResult.payorIncome) : 0
  const spousalSupportAnnual = spousalResult
    ? asNumber(spousalResult.estimatedSpousalSupportAnnual)
    : 0
  const childSupportAnnual = spousalResult
    ? asNumber(spousalResult.childSupport?.netAnnual)
    : 0
  const payorNetIncome = spousalResult ? asNumber(spousalResult.ndiPayor) : 0
  const activeTaxYear = spousalResult ? asNumber(spousalResult.taxYear, baseTaxYear) : baseTaxYear
  const recipientGrossIncome = spousalResult ? asNumber(spousalResult.recipientIncome) : 0
  const recipientNetIncome = spousalResult ? asNumber(spousalResult.ndiRecipient) : 0
  const benefitFallback = spousalResult
    ? calculateSharedCustodyBenefits(
        Math.max(payorGrossIncome - spousalSupportAnnual, 0),
        Math.max(recipientGrossIncome + spousalSupportAnnual, 0),
        asNumber(spousalResult.children, asNumber(scenario.children)),
        asNumber(spousalResult.childrenUnderSix, asNumber(scenario.childrenUnderSix)),
        activeTaxYear,
      )
    : null
  const payorBenefitBreakdown = spousalResult?.benefits?.payor ??
    benefitFallback?.payor ?? {
      canadaChildBenefitAnnual: 0,
      gstHstCreditAnnual: 0,
      bcFamilyBenefitAnnual: 0,
      bcClimateActionCreditAnnual: 0,
      totalAnnual: 0,
    }
  const recipientBenefitBreakdown = spousalResult?.benefits?.recipient ??
    benefitFallback?.recipient ?? {
      canadaChildBenefitAnnual: 0,
      gstHstCreditAnnual: 0,
      bcFamilyBenefitAnnual: 0,
      bcClimateActionCreditAnnual: 0,
      totalAnnual: 0,
    }
  const payorTaxAfterSupport = spousalResult
    ? asNumber(
        spousalResult.payorTax,
        calculateApproxBcTax(payorGrossIncome - spousalSupportAnnual, activeTaxYear),
      )
    : 0
  const payorTaxBeforeSupportDeduction = spousalResult
    ? asNumber(
        spousalResult.payorTaxBeforeSupportDeduction,
        calculateApproxBcTax(payorGrossIncome, activeTaxYear),
      )
    : 0
  const payorTaxDeductionBenefit = spousalResult
    ? asNumber(
        spousalResult.payorTaxDeductionBenefit,
        Math.max(payorTaxBeforeSupportDeduction - payorTaxAfterSupport, 0),
      )
    : 0
  const recipientGovernmentBenefits = spousalResult
    ? asNumber(recipientBenefitBreakdown.totalAnnual)
    : 0
  const recipientTaxBeforeSupportInclusion = spousalResult
    ? asNumber(
        spousalResult.recipientTaxBeforeSupportInclusion,
        calculateApproxBcTax(recipientGrossIncome, activeTaxYear),
      )
    : 0
  const recipientTaxSupportCost = spousalResult
    ? asNumber(
        spousalResult.recipientTaxSupportCost,
        Math.max(
          asNumber(
            spousalResult.recipientTax,
            calculateApproxBcTax(recipientGrossIncome + spousalSupportAnnual, activeTaxYear),
          ) - recipientTaxBeforeSupportInclusion,
          0,
        ),
      )
    : 0
  const payorEquivalentBeforeTaxIncome = spousalResult
    ? calculateEquivalentBeforeTaxIncome(payorNetIncome, activeTaxYear)
    : 0
  const recipientEquivalentBeforeTaxIncome = spousalResult
    ? calculateEquivalentBeforeTaxIncome(recipientNetIncome, activeTaxYear)
    : 0
  const netIncomeDivisor = netIncomePeriod === 'monthly' ? 12 : 1
  const netIncomeColumnLabel = netIncomePeriod === 'monthly' ? 'Monthly amount' : 'Annual amount'
  const netIncomeRawRows = spousalResult
    ? [
        ['Gross income', payorGrossIncome, recipientGrossIncome],
        ['Child support', -childSupportAnnual, childSupportAnnual],
        ['Spousal support (pre-tax)', -spousalSupportAnnual, spousalSupportAnnual],
        ['Spousal support (tax deduction)', payorTaxDeductionBenefit, -recipientTaxSupportCost],
        [
          'Canada child benefit',
          payorBenefitBreakdown.canadaChildBenefitAnnual,
          recipientBenefitBreakdown.canadaChildBenefitAnnual,
        ],
        [
          'GST/HST credit',
          payorBenefitBreakdown.gstHstCreditAnnual,
          recipientBenefitBreakdown.gstHstCreditAnnual,
        ],
        [
          'B.C. family benefit',
          payorBenefitBreakdown.bcFamilyBenefitAnnual,
          recipientBenefitBreakdown.bcFamilyBenefitAnnual,
        ],
        ...((payorBenefitBreakdown.bcClimateActionCreditAnnual > 0 ||
        recipientBenefitBreakdown.bcClimateActionCreditAnnual > 0)
          ? [
              [
                'B.C. climate action credit',
                payorBenefitBreakdown.bcClimateActionCreditAnnual,
                recipientBenefitBreakdown.bcClimateActionCreditAnnual,
              ],
            ]
          : []),
        ['Income tax', -payorTaxBeforeSupportDeduction, -recipientTaxBeforeSupportInclusion],
        ['Estimated net income', payorNetIncome, recipientNetIncome],
        [
          'Equivalent before-tax income',
          payorEquivalentBeforeTaxIncome,
          recipientEquivalentBeforeTaxIncome,
        ],
      ]
    : []
  const unsignedNetIncomeLabels = new Set([
    'Gross income',
    'Estimated net income',
    'Equivalent before-tax income',
  ])
  const netIncomeDisplayRows = netIncomeRawRows.map(([label, payorValue, recipientValue]) => {
    const scale = netIncomeDivisor
    const signed = !unsignedNetIncomeLabels.has(label)
    const isEquivalentIncomeRow = label === 'Equivalent before-tax income'
    const labelCell = isEquivalentIncomeRow
      ? {
          key: `${label}-label`,
          className: 'data-table__informational',
          content: (
            <span className="info-label">
              <em>{label}</em>
              <span
                className="info-icon"
                title="The gross employment income that would leave the same after-tax income if there were no child support, spousal support, or government benefits."
                aria-label="Equivalent before-tax income explanation"
              >
                (i)
              </span>
            </span>
          ),
        }
      : label
    const valueClassName = isEquivalentIncomeRow ? 'data-table__informational' : ''

    return [
      labelCell,
      {
        key: `${label}-payor`,
        className: valueClassName,
        content: <CurrencyCell value={payorValue / scale} signed={signed} />,
      },
      {
        key: `${label}-recipient`,
        className: valueClassName,
        content: <CurrencyCell value={recipientValue / scale} signed={signed} />,
      },
    ]
  })
  return (
    <div className="app-shell">
      <header className="toolbar">
        <div>
          <h1>Canadian Support Calculator</h1>
          <p>British Columbia child support and spousal support estimates.</p>
        </div>
      </header>

      <main className="workspace">
        <aside className="sidebar-panel">
          <section className="panel-section">
            <h2>Scenario</h2>
            <form className="scenario-form" onSubmit={handleSubmit}>
              <div className="form-grid">
                <label>
                  Jurisdiction
                  <select
                    name="jurisdiction"
                    value={scenario.jurisdiction}
                    onChange={handleScenarioChange}
                  >
                    <option value="BC">British Columbia</option>
                  </select>
                </label>

                <label>
                  Children
                  <select
                    name="children"
                    value={scenario.children}
                    onChange={handleScenarioChange}
                  >
                    {supportedChildren.map((count) => (
                      <option key={count} value={count}>
                        {count}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Children under 6
                  <input
                    name="childrenUnderSix"
                    type="number"
                    min="0"
                    max={scenario.children}
                    step="1"
                    value={scenario.childrenUnderSix}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  Tax year
                  <input
                    name="taxYear"
                    type="number"
                    min="1"
                    step="1"
                    value={scenario.taxYear}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  Payor income
                  <input
                    name="payorIncome"
                    type="number"
                    min="0"
                    step="100"
                    value={scenario.payorIncome}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  Recipient income
                  <input
                    name="recipientIncome"
                    type="number"
                    min="0"
                    step="100"
                    value={scenario.recipientIncome}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  Target minimum %
                  <input
                    name="targetMinPercent"
                    type="number"
                    min="1"
                    max="99"
                    step="0.5"
                    value={scenario.targetMinPercent}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  Target maximum %
                  <input
                    name="targetMaxPercent"
                    type="number"
                    min="1"
                    max="99"
                    step="0.5"
                    value={scenario.targetMaxPercent}
                    onChange={handleScenarioChange}
                  />
                </label>
              </div>

              <div className="form-actions">
                <label className="form-toggle">
                  <input
                    name="autoRecalculate"
                    type="checkbox"
                    checked={autoRecalculate}
                    onChange={(event) => setAutoRecalculate(event.target.checked)}
                  />
                  <span>Recalculate automatically</span>
                </label>
                <button type="submit" disabled={isCalculating || autoRecalculate}>
                  {isCalculating ? 'Calculating' : 'Recalculate'}
                </button>
                <button type="button" className="button-secondary" onClick={handleReset}>
                  Restore example
                </button>
              </div>
            </form>
          </section>
        </aside>

        <section className="results-panel">
          <section className="panel-section">
            <div className="section-header">
              <div>
                <h2>Net Income</h2>
                <p>Estimated annual income after tax, child support, spousal support, and benefits.</p>
              </div>
              <div className="view-toggle" role="group" aria-label="Net income period">
                <button
                  type="button"
                  className={netIncomePeriod === 'annual' ? 'is-active' : ''}
                  aria-pressed={netIncomePeriod === 'annual'}
                  onClick={() => setNetIncomePeriod('annual')}
                >
                  Annual
                </button>
                <button
                  type="button"
                  className={netIncomePeriod === 'monthly' ? 'is-active' : ''}
                  aria-pressed={netIncomePeriod === 'monthly'}
                  onClick={() => setNetIncomePeriod('monthly')}
                >
                  Monthly
                </button>
              </div>
            </div>

            {spousalError ? <p className="error-text">{spousalError}</p> : null}

            {spousalResult ? (
              <ResultTable
                caption="Net income calculation"
                columns={['Component', `Payor ${netIncomeColumnLabel}`, `Recipient ${netIncomeColumnLabel}`]}
                rows={netIncomeDisplayRows}
                numericColumnIndexes={[1, 2]}
              />
            ) : (
              <p className="empty-state">Results will appear here after the first calculation.</p>
            )}
          </section>

          <section className="panel-section">
            <div className="section-header">
              <div>
                <h2>Calculation Details</h2>
                <p>Child support and spousal-support iteration details for the current scenario.</p>
              </div>
              <button
                type="button"
                className="drawer-toggle"
                aria-expanded={spousalDetailsOpen}
                onClick={() => setSpousalDetailsOpen((current) => !current)}
              >
                {spousalDetailsOpen ? 'Hide Details' : 'Show Details'}
              </button>
            </div>

            {childError ? <p className="error-text">{childError}</p> : null}
            {spousalError ? <p className="error-text">{spousalError}</p> : null}

            {childResult || spousalResult ? (
              <div
                className={`details-drawer ${spousalDetailsOpen ? 'details-drawer--open' : 'details-drawer--closed'}`}
              >
                <div className="details-drawer__content">
                  {childResult ? (
                    <section className="details-block">
                      <div className="details-block__header">
                        <h3>Child support</h3>
                        <strong>{formatCurrency(childResult.netMonthly)}</strong>
                      </div>
                      <p>Monthly table amounts with offset calculation.</p>
                      <DetailList
                        emphasis
                        items={[
                          {
                            label: 'Transfer direction',
                            value:
                              childResult.direction === 'payor_to_recipient'
                                ? 'Payor to recipient'
                                : childResult.direction === 'recipient_to_payor'
                                  ? 'Recipient to payor'
                                  : 'No transfer',
                          },
                          { label: 'Net monthly transfer', value: formatCurrency(childResult.netMonthly) },
                          { label: 'Net annual transfer', value: formatCurrency(childResult.netAnnual) },
                        ]}
                      />
                      <ResultTable
                        caption="Child support amounts"
                        columns={['Party', 'Monthly', 'Annual']}
                        rows={childRows}
                        numericColumnIndexes={[1, 2]}
                      />
                    </section>
                  ) : null}

                  {spousalResult ? (
                    <section className="details-block">
                      <div className="details-block__header">
                        <h3>Spousal support calculations</h3>
                        <strong>{formatCurrency(spousalResult.estimatedSpousalSupportMonthly)}</strong>
                      </div>
                      <p>Iteration details used to place the recipient inside the selected NDI range.</p>
                      <DetailList
                        emphasis
                        items={[
                          {
                            label: 'Estimated monthly spousal support',
                            value: formatCurrency(spousalResult.estimatedSpousalSupportMonthly),
                          },
                          {
                            label: 'Estimated annual spousal support',
                            value: formatCurrency(spousalResult.estimatedSpousalSupportAnnual),
                          },
                          {
                            label: 'Recipient share of NDI',
                            value: formatPercent(spousalResult.recipientSharePercent),
                          },
                          {
                            label: 'Iterations',
                            value: String(spousalResult.iterations),
                          },
                        ]}
                      />
                      <ResultTable
                        caption="Net disposable income"
                        columns={['Party', 'NDI']}
                        rows={[
                          ['Payor', formatCurrency(spousalResult.ndiPayor)],
                          ['Recipient', formatCurrency(spousalResult.ndiRecipient)],
                          ['Child support annual', formatCurrency(spousalResult.childSupport.netAnnual)],
                          ['Recipient benefits annual', formatCurrency(recipientGovernmentBenefits)],
                        ]}
                        numericColumnIndexes={[1]}
                      />
                      <ResultTable
                        caption="Recent iterations"
                        columns={['Iteration', 'Spousal support', 'Recipient NDI share']}
                        rows={spousalHistoryRows}
                        numericColumnIndexes={[1]}
                      />
                    </section>
                  ) : null}
                </div>
              </div>
            ) : (
              <p className="empty-state">Results will appear here after the first calculation.</p>
            )}
          </section>

        </section>

        <section className="panel-section workspace__full">
          <h2>References</h2>
          <DetailList
            items={[
              {
                label: 'Supported child counts',
                value: supportedChildren.length ? supportedChildren.join(', ') : 'Loading',
              },
              {
                label: 'Target range',
                value: `${scenario.targetMinPercent}% to ${scenario.targetMaxPercent}% recipient NDI`,
              },
              {
                label: 'Children under 6',
                value: scenario.childrenUnderSix,
              },
              {
                label: 'Tax year',
                value: scenario.taxYear,
              },
              {
                label: 'Data note',
                value: metadata?.disclaimer ?? 'Loading',
              },
              {
                label: 'Benefit assumptions',
                value: metadata?.benefitAssumptions ?? 'Loading',
              },
              {
                label: 'Children note',
                value: metadata?.supportedChildrenNote ?? 'Loading',
              },
            ]}
          />
          {metadataError ? <p className="error-text">{metadataError}</p> : null}
        </section>
      </main>
    </div>
  )
}

export default App
