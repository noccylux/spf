from os.path import join
from libs.functions import *
from libs.dataProcess import DataProcess
import xarray as xr
import torch
import numpy as np


class DataSet:
    r"""
    生成滑动窗口数据，每步返回两个值: trainData 和 targetData
    trainData.shape = torch.Size([trainDays, stocksNum, parametersNum])
    torch.Size([targetDays, stocksNum])
    trainDays 与 targetDays可使用 setLength 函数更改

    isel 函数：对数据进行切片，需要输入切片的开始和结束索引，以及进行切片操作的维度
    """

    def __init__(self, data: xr.DataArray = None, dataSetPath: str = None,
                 trainDays: int = 360, targetDays: int = 30,
                 device=None):
        self.device = device  # 自动将tensor转移device，device==None则不转移(默认使用CPU)
        self.data: xr.DataArray = xr.DataArray([])
        if data is not None:
            self.data = data
        elif dataSetPath is not None:
            self.data = xr.load_dataarray(dataSetPath)
        else:
            raise "data not found"
        self.data.load()
        self.data = self.data.astype(np.float32)
        self.indexList = [i for i in range(len(self.data.Date))]  # 不知道怎么从xr.DataArray中获取一段时间的切片，用这种方法代替
        self.trainDays: int = trainDays
        self.targetDays: int = targetDays

    def isel(self, startIndex: int, endIndex: int, dim: str = "Date", inplace: bool = True):
        """
        use like   dataSet.sel(index=[0: 3000])
        or         trainDataSet = dataSet.sel(index=[0: 3000], inplace=False)
        """
        if inplace:
            eval("self.data = self.data.isel(" + dim + "=self.indexList[startIndex: endIndex])")
            return self.data
        else:
            return eval("self.data.isel(" + dim + "=self.indexList[startIndex: endIndex])")

    def setLength(self, trainDays, targetDays):
        self.trainDays = trainDays
        self.targetDays = targetDays

    def getTrainData(self, item: int):
        r"""
        data.nc中获取的是[-1, 1440, 10]的数据，需要转换为[-1, 120, 120]的数据
        在使用返回的数据时，需要使用 trainData.reshape(360, 1, 120, 120)
            reshape的工作方式:
                                            0, 1, 2, 3
               0, 1, 2, 3, 4, 5, 6, 7  ->   4, 5, 6, 7
               9, 8, 7, 6, 5, 4, 3, 2  ->   9, 8, 7, 6
                                            5, 4, 3, 2
        :return: torch.Size([trainDays, stocksNum, parametersNum]) like torch.Size([360, 1570, 9])
        """
        if self.device is None:
            return torch.Tensor(self.data.isel(Date=self.indexList[item: item + self.trainDays]).values)
        else:
            return torch.Tensor(self.data.isel(Date=self.indexList[item: item + self.trainDays]).values).to(self.device)

    def getTargetData(self, item: int):
        r"""
        :return: torch.Size([targetDays, stocksNum]) like torch.Size([30, 1570])
        """
        if self.device is None:
            return torch.Tensor(self.data
                                .isel(Date=self.indexList[item + self.trainDays: item + self.trainDays + self.targetDays])
                                .sel(Parameter="close")
                                .values)
        else:
            return torch.Tensor(self.data
                                .isel(Date=self.indexList[item + self.trainDays: item + self.trainDays + self.targetDays])
                                .sel(Parameter="close")
                                .values).to(self.device)

    def __getitem__(self, item):
        return self.getTrainData(item), self.getTargetData(item)

    def __len__(self):
        return len(self.data.Date)


class DataLoader:
    def __init__(self, dataSet: DataSet):
        self.dataSet: DataSet = dataSet
        self.shifter: int = -1
        self.len = len(self.dataSet) - (self.dataSet.trainDays + self.dataSet.targetDays) + 1

    def __len__(self):
        return self.len

    def __iter__(self):
        return self

    def __next__(self):
        self.shifter += 1
        if self.shifter < self.len:
            return self.dataSet[self.shifter]
        else:
            raise StopIteration
